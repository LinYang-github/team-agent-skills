#!/usr/bin/env perl
# JSON::PP, Encode, File::Temp are Perl core modules. Never execute agent text.
use strict;
use warnings;
use utf8;
use JSON::PP qw(decode_json);
use Encode qw(encode_utf8 decode_utf8);
use File::Temp qw(tempfile);
binmode STDERR, ':encoding(UTF-8)';
my $rules = shift @ARGV;
my $raw = do { local $/; <STDIN> };
my $input = eval { decode_json($raw // '') };
if ($@ || ref($input) ne 'HASH') {
    print STDERR "Agent 钩子 JSON 无效，请检查 PreToolUse 配置。\n";
    exit 1;
}
my $tool = $input->{tool_input} // $input->{toolInput} // {};
if (ref($tool) ne 'HASH') {
    print STDERR "Agent 钩子 tool_input 必须是对象，请检查 PreToolUse 配置。\n";
    exit 1;
}
my $command = $tool->{command} // $tool->{cmd} // '';
# Codex may pass argv, e.g. ["zsh", "-lc", "git switch -c x"].
my $argv;
if (ref($command) eq 'ARRAY') {
    exit 0 if grep { ref($_) || !defined($_) } @$command;
    $argv = $command;
    exit 0 unless @$argv;
} elsif (ref($command) || !length($command)) {
    exit 0;
}
my $cwd = $tool->{workdir} // $tool->{cwd} // $input->{cwd};
if (defined $cwd && !chdir encode_utf8($cwd)) {
    print STDERR "无法进入 Agent 命令目录，请检查 tool_input.workdir / cwd。\n";
    exit 1;
}

sub validate {
    my ($mode, $value) = @_;
    if ($mode eq 'commit-msg') {
        my ($fh, $path) = tempfile('team-standards-XXXXXX', TMPDIR => 1, UNLINK => 1);
        binmode $fh, ':encoding(UTF-8)';
        print $fh $value;
        close $fh;
        system 'sh', $rules, $mode, $path;
    } else {
        system 'sh', $rules, $mode, encode_utf8($value);
    }
    exit($? == -1 ? 1 : ($? >> 8)) if $?;
}

# Small literal-shell lexer: quotes, escapes and command separators are handled
# without eval. Variables/substitutions/aliases are intentionally not interpreted;
# actual commit/push inputs are enforced by the installed Git hooks.
sub commands {
    my ($text) = @_;
    my (@result, @words);
    my ($word, $quote, $active) = ('', '', 0);
    for (my $i = 0; $i < length($text); $i++) {
        my $ch = substr($text, $i, 1);
        if ($quote eq "'") {
            if ($ch eq "'") { $quote = ''; } else { $word .= $ch; }
        } elsif ($ch eq '\\' && $quote ne "'") {
            my $next = substr($text, $i + 1, 1);
            if ($quote eq '"' && $next !~ /[\$`"\\\n]/) { $word .= $ch; }
            else { $i++; $word .= $next unless $next eq "\n"; }
            $active = 1;
        } elsif ($quote eq '"') {
            if ($ch eq '"') { $quote = ''; } else { $word .= $ch; }
        } elsif ($ch eq "'" || $ch eq '"') {
            $quote = $ch; $active = 1;
        } elsif ($ch eq '#' && !$active) {
            $i++ while $i < length($text) && substr($text, $i, 1) ne "\n";
            $i--;
        } elsif ($ch =~ /[\s;&|()]/) {
            push @words, $word if $active;
            ($word, $active) = ('', 0);
            if ($ch =~ /[\n;&|()]/ && @words) { push @result, [@words]; @words = (); }
        } else { $word .= $ch; $active = 1; }
    }
    if (length $quote) {
        print STDERR "Shell 命令引号不完整，请检查后重试。\n";
        exit 1;
    }
    push @words, $word if $active;
    push @result, [@words] if @words;
    return @result;
}

sub git_read {
    my (@args) = @_;
    # Read-only Git invocation with explicit argv; stderr is suppressed for non-repos.
    my $pid = open my $fh, '-|';
    return '' unless defined $pid;
    if (!$pid) {
        open STDERR, '>', File::Spec->devnull();
        exec 'git', map { encode_utf8($_) } @args;
        exit 1;
    }
    local $/;
    my $value = <$fh> // '';
    close $fh;
    $value =~ s/\s+$//;
    return decode_utf8($value);
}

sub push_check {
    my ($context, @args) = @_;
    my (@positionals, $all, $delete, $tags);
    while (@args) {
        my $arg = shift @args;
        if ($arg eq '--repo') { shift @args; push @positionals, '__remote__'; }
        elsif ($arg =~ /^--repo=/) { push @positionals, '__remote__'; }
        elsif ($arg eq '--all' || $arg eq '--mirror' || $arg eq '--branches') { $all = 1; }
        elsif ($arg eq '--delete' || $arg eq '-d') { $delete = 1; }
        elsif ($arg eq '--tags') { $tags = 1; }
        elsif ($arg eq '-o' || $arg eq '--push-option' || $arg eq '--receive-pack' || $arg eq '--exec') { shift @args; }
        elsif ($arg eq '--') { push @positionals, @args; last; }
        elsif ($arg !~ /^-/) { push @positionals, $arg; }
    }
    my $remote = shift @positionals;
    return if $delete; # Python pre-push policy skips ref deletions.
    return if $tags && !$all && !@positionals;
    if (!defined $remote) {
        my $branch = git_read(@$context, 'branch', '--show-current');
        $remote = git_read(@$context, 'config', '--get', "branch.$branch.pushRemote") ||
                  git_read(@$context, 'config', '--get', 'remote.pushDefault') ||
                  git_read(@$context, 'config', '--get', "branch.$branch.remote") || 'origin';
    }
    my @destinations;
    if ($all) {
        @destinations = split /\n/, git_read(@$context, 'for-each-ref', '--format=%(refname:short)', 'refs/heads');
    } elsif (@positionals) {
        for my $ref (@positionals) {
            $ref =~ s/^\+//;
            next if $ref =~ /^:/; # deletion or matching ':' (handled below)
            my ($source, $dest) = split /:/, $ref, 2;
            $dest = $source unless defined $dest;
            next if $dest =~ m{^refs/(?!heads/)};
            if ($dest eq 'HEAD') { $dest = git_read(@$context, 'branch', '--show-current'); }
            $dest =~ s{^refs/heads/}{};
            push @destinations, $dest if length $dest && $dest !~ /\*/;
        }
        if (grep { $_ eq ':' || /\*/ } @positionals) {
            push @destinations, split /\n/, git_read(@$context, 'for-each-ref', '--format=%(refname:short)', 'refs/heads');
        }
    } else {
        # Configured refspecs and upstream destinations can differ from local names.
        my $configured = defined($remote) ? git_read(@$context, 'config', '--get-all', "remote.$remote.push") : '';
        if (length $configured) { return push_check($context, $remote, split /\n/, $configured); }
        my $upstream = git_read(@$context, 'rev-parse', '--symbolic-full-name', '@{push}');
        $upstream =~ s{^refs/remotes/[^/]+/}{};
        push @destinations, $upstream if length $upstream;
        push @destinations, git_read(@$context, 'branch', '--show-current');
    }
    my $sha = '1' x 40;
    open my $fh, '|-', 'sh', $rules, 'pre-push' or exit 1;
    binmode $fh, ':encoding(UTF-8)';
    for my $dest (@destinations) {
        print $fh "HEAD $sha refs/heads/$dest $sha\n" if length $dest;
    }
    close $fh;
    exit($? == -1 ? 1 : ($? >> 8)) if $?;
}

use File::Spec;
# The script argument of `sh -c`, `bash -lc`, `zsh -l -c`, `pwsh -Command`.
sub wrapped_script {
    my (@words) = @_;
    my $shell = shift @words;
    if ($shell =~ m{(?:^|[/\\])(?:ba|z|da|k)?sh(?:\.exe)?$}i) {
        my $has_c;
        while (@words && $words[0] =~ /^-/ && $words[0] ne '--') {
            my $opt = shift @words;
            $has_c = 1 if $opt =~ /^-[A-Za-z]*c[A-Za-z]*$/;
            shift @words if $opt =~ /^[-+]o$/ && @words; # -o option-name
        }
        return $has_c && @words ? $words[0] : undef;
    }
    if ($shell =~ m{(?:^|[/\\])(?:pwsh|powershell)(?:\.exe)?$}i) {
        for (my $i = 0; $i < @words; $i++) {
            return join(' ', @words[$i + 1 .. $#words])
                if $words[$i] =~ /^-(?:c|command)$/i && $i + 1 < @words;
        }
    }
    return undef;
}

my @queue = $argv ? ([@$argv]) : commands($command);
while (@queue) {
    my @words = @{shift @queue};
    shift @words while @words && ($words[0] =~ /^[A-Za-z_][A-Za-z_0-9]*=/ || $words[0] =~ /^(?:env|command|exec)$/);
    next unless @words;
    my $script = wrapped_script(@words);
    if (defined $script) { push @queue, commands($script); next; }
    next unless shift(@words) =~ m{(?:^|[/\\])git(?:\.exe)?$};
    my @context;
    while (@words && $words[0] =~ /^-/) {
        my $arg = shift @words;
        push @context, $arg;
        push @context, shift @words if $arg =~ /^(?:-C|-c|--git-dir|--work-tree)$/ && @words;
    }
    my $verb = shift(@words) // '';
    if ($verb eq 'checkout' || $verb eq 'switch') {
        for (my $i = 0; $i < @words; $i++) {
            my $arg = $words[$i];
            last if $arg eq '--';
            if (($verb eq 'checkout' && $arg =~ /^-[bB]$/) ||
                ($verb eq 'switch' && $arg =~ /^(?:-[cC]|--create|--force-create)$/)) {
                validate('branch', $words[++$i]) if $i + 1 < @words;
            } elsif (($verb eq 'checkout' && $arg =~ /^-[bB](.+)$/) ||
                     ($verb eq 'switch' && $arg =~ /^(?:-[cC]|--(?:force-)?create=)(.+)$/)) {
                validate('branch', $1);
            }
        }
    } elsif ($verb eq 'worktree') {
        next unless @words && shift(@words) eq 'add';
        for (my $i = 0; $i < @words; $i++) {
            last if $words[$i] eq '--';
            if ($words[$i] =~ /^-[bB]$/) { validate('branch', $words[++$i]) if $i + 1 < @words; }
            elsif ($words[$i] =~ /^-[bB](.+)$/) { validate('branch', $1); }
        }
    } elsif ($verb eq 'branch') {
        # Listing, deleting, renaming, copying and upstream operations do not create
        # a branch via `git branch <name>` and must not be mistaken for that form.
        next if grep { /^(?:-[aAvvldDmMcCr]|--(?:list|all|remotes|delete|move|copy|show-current|contains|no-contains|merged|no-merged|set-upstream-to|unset-upstream|edit-description|format|points-at))(?:=|$)/ } @words;
        shift @words while @words && ($words[0] eq '-f' || $words[0] eq '--force' || $words[0] eq '--');
        validate('branch', $words[0]) if @words && $words[0] !~ /^-/;
    } elsif ($verb eq 'commit') {
        my @messages;
        for (my $i = 0; $i < @words; $i++) {
            my $arg = $words[$i];
            last if $arg eq '--';
            if ($arg =~ /^-[a-zA-Z]*m$/ || $arg eq '--message') { push @messages, $words[++$i] if $i + 1 < @words; }
            elsif ($arg =~ /^--message=(.*)$/s || $arg =~ /^-[a-zA-Z]*m(.+)$/s) { push @messages, $1; }
        }
        validate('commit-msg', join("\n\n", @messages)) if @messages;
    } elsif ($verb eq 'push') { push_check(\@context, @words); }
}
exit 0;
