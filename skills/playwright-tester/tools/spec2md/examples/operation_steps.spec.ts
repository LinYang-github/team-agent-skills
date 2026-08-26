import { expect, test } from '@playwright/test';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __filenameDir = path.dirname(__filename);

test.describe('用户手册步骤转换示例', () => {
  test('新建评估任务分类', async ({ page }) => {
    // manual-title: 新建评估任务分类
    // input: 名称、创建人、备注
    // output: 评估任务分类创建成功
    await page.goto('http://127.0.0.1:3001/evaluation/tasks');

    // manual: 在评估任务管理主界面，点击“新建分类”按钮，进入新建分类界面
    await page.getByRole('button', { name: '新建分类' }).click();
    await expect(page.getByRole('dialog', { name: '新建分类' })).toBeVisible();
    // figure: 新建分类界面
    await page.screenshot({
      path: path.join(__filenameDir, 'test-images', '新建评估任务分类', '新建评估任务分类_step_001.png'),
      fullPage: true,
      animations: 'disabled',
    });

    // manual: 填写名称、创建人和备注等基本信息
    await page.getByRole('textbox', { name: '名称' }).fill('软件研制评估');
    await page.getByRole('textbox', { name: '创建人' }).fill('张三');
    await page.getByRole('textbox', { name: '备注' }).fill('用于软件研制项目评估任务归类');
    await expect(page.getByRole('textbox', { name: '名称' })).toHaveValue('软件研制评估');
    // figure: 分类基本信息
    await page.screenshot({
      path: path.join(__filenameDir, 'test-images', '新建评估任务分类', '新建评估任务分类_step_002.png'),
      fullPage: true,
      animations: 'disabled',
    });

    // manual: 点击“确定”按钮，完成评估任务分类的创建
    await page.getByRole('button', { name: '确定' }).click();
    await expect(page.getByText('创建成功')).toBeVisible();
  });

  test('查询评估任务分类', async ({ page }) => {
    // manual-title: 查询评估任务分类
    // input: 分类名称
    // output: 查询结果列表显示匹配的评估任务分类
    await page.goto('http://127.0.0.1:3001/evaluation/tasks');

    // manual: 在评估任务管理主界面，输入分类名称并点击“查询”按钮
    await page.getByRole('textbox', { name: '分类名称' }).fill('软件研制评估');
    await page.getByRole('button', { name: '查询' }).click();
    await expect(page.getByText('软件研制评估')).toBeVisible();
    // figure: 查询结果列表
    await page.screenshot({
      path: path.join(__filenameDir, 'test-images', '查询评估任务分类', '查询评估任务分类_step_001.png'),
      fullPage: true,
      animations: 'disabled',
    });
  });
});
