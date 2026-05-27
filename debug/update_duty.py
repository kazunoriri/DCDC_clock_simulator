"""
Excel COM オートメーションを使って duty 値を更新するスクリプト
"""
import win32com.client
import os

BASE = r'C:\Users\e12206\GitHub\DCDC_clock_simulator\設定ファイル'

# ファイルごとの変更内容: {ファイルパス: {パラメータ名: 新しい値}}
CHANGES = {
    # CLK1 (シリアル/静止画 共通)
    os.path.join(BASE, 'シリアル_48us', 'シリアル_48us_CLK1.xlsx'): {
        'power_net_duty_percent_0_min': 62,
        'power_net_duty_percent_0_max': 62,
        'power_net_duty_percent_1_min': 75,
        'power_net_duty_percent_1_max': 75,
        'power_net_duty_percent_2_min': 16,
        'power_net_duty_percent_2_max': 16,
        'power_net_duty_percent_3_min': 16,
        'power_net_duty_percent_3_max': 16,
        'power_net_duty_percent_4_min': 21,
        'power_net_duty_percent_4_max': 21,
    },
    os.path.join(BASE, '静止画_60us', '静止画_60us_CLK1.xlsx'): {
        'power_net_duty_percent_0_min': 62,
        'power_net_duty_percent_0_max': 62,
        'power_net_duty_percent_1_min': 75,
        'power_net_duty_percent_1_max': 75,
        'power_net_duty_percent_2_min': 16,
        'power_net_duty_percent_2_max': 16,
        'power_net_duty_percent_3_min': 16,
        'power_net_duty_percent_3_max': 16,
        'power_net_duty_percent_4_min': 21,
        'power_net_duty_percent_4_max': 21,
    },
    # CLK2
    os.path.join(BASE, 'シリアル_48us', 'シリアル_48us_CLK2.xlsx'): {
        'power_net_duty_percent_0_min': 62,
        'power_net_duty_percent_0_max': 62,
    },
    os.path.join(BASE, '静止画_60us', '静止画_60us_CLK2.xlsx'): {
        'power_net_duty_percent_0_min': 62,
        'power_net_duty_percent_0_max': 62,
    },
    # CLK3
    os.path.join(BASE, 'シリアル_48us', 'シリアル_48us_CLK3.xlsx'): {
        'power_net_duty_percent_0_min': 18,
        'power_net_duty_percent_0_max': 43,
    },
    os.path.join(BASE, '静止画_60us', '静止画_60us_CLK3.xlsx'): {
        'power_net_duty_percent_0_min': 18,
        'power_net_duty_percent_0_max': 43,
    },
    # CLK4
    os.path.join(BASE, 'シリアル_48us', 'シリアル_48us_CLK4.xlsx'): {
        'power_net_duty_percent_0_min': 34,
        'power_net_duty_percent_0_max': 34,
    },
    os.path.join(BASE, '静止画_60us', '静止画_60us_CLK4.xlsx'): {
        'power_net_duty_percent_0_min': 34,
        'power_net_duty_percent_0_max': 34,
    },
    # CLK5
    os.path.join(BASE, 'シリアル_48us', 'シリアル_48us_CLK5.xlsx'): {
        'power_net_duty_percent_0_min': 45,
        'power_net_duty_percent_0_max': 73,
        'power_net_duty_percent_1_min': 47,
        'power_net_duty_percent_1_max': 81,
        'power_net_duty_percent_2_min': 47,
        'power_net_duty_percent_2_max': 81,
        'power_net_duty_percent_3_min': 47,
        'power_net_duty_percent_3_max': 81,
        'power_net_duty_percent_4_min': 42,
        'power_net_duty_percent_4_max': 72,
        'power_net_duty_percent_5_min': 76,
        'power_net_duty_percent_5_max': 100,
        'power_net_duty_percent_6_min': 24,
        'power_net_duty_percent_6_max': 24,
        'power_net_duty_percent_7_min': 21,
        'power_net_duty_percent_7_max': 21,
    },
    os.path.join(BASE, '静止画_60us', '静止画_60us_CLK5.xlsx'): {
        'power_net_duty_percent_0_min': 45,
        'power_net_duty_percent_0_max': 73,
        'power_net_duty_percent_1_min': 47,
        'power_net_duty_percent_1_max': 81,
        'power_net_duty_percent_2_min': 47,
        'power_net_duty_percent_2_max': 81,
        'power_net_duty_percent_3_min': 47,
        'power_net_duty_percent_3_max': 81,
        'power_net_duty_percent_4_min': 42,
        'power_net_duty_percent_4_max': 72,
        'power_net_duty_percent_5_min': 76,
        'power_net_duty_percent_5_max': 100,
        'power_net_duty_percent_6_min': 24,
        'power_net_duty_percent_6_max': 24,
        'power_net_duty_percent_7_min': 21,
        'power_net_duty_percent_7_max': 21,
    },
}


def update_file(excel_app, filepath, changes):
    print(f'Opening: {os.path.basename(filepath)}')
    wb = excel_app.Workbooks.Open(filepath)
    try:
        ws = wb.Sheets('config')
        # B列の最終行を取得
        last_row = ws.UsedRange.Rows.Count
        updated = []
        for row in range(1, last_row + 1):
            param = ws.Cells(row, 1).Value
            if param in changes:
                old_val = ws.Cells(row, 2).Value
                new_val = changes[param]
                ws.Cells(row, 2).Value = new_val
                updated.append(f'  {param}: {old_val} -> {new_val}')
        wb.Save()
        for u in updated:
            print(u)
        print(f'  Saved.')
    finally:
        wb.Close(SaveChanges=False)


def main():
    excel = win32com.client.Dispatch('Excel.Application')
    excel.Visible = False
    excel.DisplayAlerts = False
    try:
        for filepath, changes in CHANGES.items():
            update_file(excel, filepath, changes)
    finally:
        excel.Quit()
    print('\nAll done.')


if __name__ == '__main__':
    main()
