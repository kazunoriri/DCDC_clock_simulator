import openpyxl, os, glob

base = r'C:\Users\e12206\GitHub\DCDC_clock_simulator\設定ファイル'
files = glob.glob(os.path.join(base, '**', '*.xlsx'), recursive=True)
for f in sorted(files):
    wb = openpyxl.load_workbook(f, data_only=True)
    ws = wb['config']
    print(f'=== {os.path.basename(f)} ===')
    for row in ws.iter_rows(values_only=True):
        if row[0] and ('power_net_name' in str(row[0]) or 'pl_dcdc_clk_name' in str(row[0])):
            print(f'  {row[0]}: {row[1]}')
    wb.close()
