import pandas as pd
import sys
from datetime import datetime, timedelta

import string
abc = string.ascii_lowercase.upper()

###############################
########## PARAMETER ##########
###############################

# Input File
input_dir = sys.argv[1]

# Output Path
output_dir = sys.argv[2]

###############################
############ UTILS ############
###############################

def days_between(d1, d2):

    try:
        d1 = datetime.strptime(d1, "%d.%m.%Y")
    except:
        print(d1)
        pass
    try:
        d2 = datetime.strptime(d2, "%d.%m.%Y")
    except:
        pass   
    return abs((d2 - d1).days)

def string_to_date(d1):
    try:
        d1 = datetime.strptime(d1, "%d.%m.%Y")
    except:
        pass
    return d1

def day_series(start, ende):
    sdate = string_to_date(start)
    edate = string_to_date(ende)
    return [str(day)[:10] for day in pd.date_range(sdate,edate-timedelta(days=1),freq='d')] + [edate.strftime('%Y-%m-%d')]

def german_date(date_string):
    return date_string[-2:]+'.'+date_string[5:7]+'.'+date_string[:4]

def german_style(string):
    string = string.replace(',',';')
    string = string.replace('.',',')
    string = string.replace(';','.')
    return string

###############################
####### TRANSFORMATION ########
###############################

# Load DataFrame
df = pd.read_excel(input_dir)

# Info Box
info_box_values = df.dropna(how='all').iloc[:13,2].dropna(how='all').tolist()
handling_tech_fee = round(sum(df.iloc[df[df['Unnamed: 1']=='Handling & Tech-Fee'].index[0],3:].fillna(0).tolist()),2)

# Row 23 will become header
df.columns = df.iloc[23]

# Slice dataframe and remove NaN rows
df = df.iloc[24:,1:29].dropna(how='all').reset_index(drop=True)

remove_rows = [
    'Trailer-Push',
    'TOTAL Trailer-Push',
    'Release',
    'TOTAL Release',
    'Pre-Launch/Post Launch Ongoing',
    'TOTAL Pre-Launch/Post Launch Ongoing',
    'Post-Release',
    'TOTAL Post-Release',
    'TOTAL'
]

# Remove unwanted rows
df = df[~df.isin(remove_rows)]

# Remove targeting = kostenblocker
df = df[~df['Targeting'].str.contains('kostenblocker').fillna(False)]
df = df[~df['Publisher'].str.contains('Kostenplan').fillna(False)]

# Remove NaN
df = df[df['Publisher'].notna()]
df = df[df['Start'].notna()]

def string_to_perc(x):
    try:
        x = x.replace(',','.')
        return float(x.strip('%'))/100
    except:
        return x

zgr = df.iloc[:,df.columns.get_loc("Handling & Tech-Fee")+1:].fillna(0)
for col in zgr.columns:
    zgr[col] = zgr[col].apply(lambda x: string_to_perc(x))

zielgrp = pd.DataFrame(zgr.multiply(df["Media Budget n/n/-"], axis="index").sum(), columns=['Budget']).reset_index()
zielgrp.columns = ['ZielGruppe', 'Share']
zielgrp = zielgrp[zielgrp['Share']>0]
zielgrp['Share'] = zielgrp['Share'] / zielgrp['Share'].sum()

## BUDGET TABLE ##
df_timeline = df[['Start','Ende','Media Budget n/n/-']].dropna()
df_timeline['date_series'] = df_timeline.apply(lambda x: day_series(x['Start'],x['Ende']), axis=1)
series_budget = df_timeline['Media Budget n/n/-'].tolist()
series_date = df_timeline['date_series'].tolist()

date_filter = []
date_list = []
budget_list = []
for i in range(len(df_timeline)):
    nb_of_days = len(series_date[i])
    for j in series_date[i]:
        date_list.append(german_date(j))
        date_filter.append(j)
        budget_list.append(series_budget[i]/nb_of_days)
        
graph_budget = pd.DataFrame({'Tag':date_list, 'Budget':budget_list, 'Filter':date_filter })
graph_budget = graph_budget.groupby(['Filter','Tag']).sum().reset_index(drop=False)[['Tag', 'Budget']]

## DATENSTRATEGY TABLE ##
data_strategy = df.groupby('Targeting').agg({'Media Budget n/n/-':'sum'}).sort_values('Media Budget n/n/-', ascending=False).reset_index(drop=False)
strategy = data_strategy['Targeting'].tolist()[:4]+['(Andere)']
budget = data_strategy['Media Budget n/n/-'].tolist()[:4]+[sum(data_strategy['Media Budget n/n/-'].tolist()[4:])]
data_strategy = pd.DataFrame({'Datenstrategie':strategy , 'Share':budget})
data_strategy['Share'] = round((data_strategy['Share'] / data_strategy['Share'].sum()),2)
data_strategy['Datenstrategie'] = data_strategy['Datenstrategie'].apply(lambda x: x[:30])

## CHANNEL TABLE ##    
df_channel = df.groupby('Disney Kanal').agg({'Media Budget n/n/-':'sum'}).sort_values('Media Budget n/n/-', ascending=False).reset_index(drop=False)
df_channel.columns = ['Kanal','Share']
df_channel['Share'] = round((df_channel['Share'] / df_channel['Share'].sum()),2)

## DEVICE TABLE ##
df_device = df[['Media Budget n/n/-','Desktop %','Tablet %','Mobile %','Smart TV %']]
df_device = df_device[df_device['Media Budget n/n/-'].notna()]
df_device['desktop'] = df['Media Budget n/n/-'] * df['Desktop %']
df_device['tablet'] = df['Media Budget n/n/-'] * df['Tablet %']
df_device['mobile'] = df['Media Budget n/n/-'] * df['Mobile %']
df_device['smarttv'] = df['Media Budget n/n/-'] * df['Smart TV %']

device_share = [
    round((df_device['desktop'].sum()/df_device['Media Budget n/n/-'].sum()),2),
    round((df_device['tablet'].sum()/df_device['Media Budget n/n/-'].sum()),2),
    round((df_device['mobile'].sum()/df_device['Media Budget n/n/-'].sum()),2),
    round((df_device['smarttv'].sum()/df_device['Media Budget n/n/-'].sum()),2)
]

graph_device = pd.DataFrame({'Device':['Desktop','Tablet','Mobile','Smart TV'],
                             'Share':device_share})

# Info Box Data
df_sl_views = df['est. Views'].sum()

## MAIN TABLE
df_main = df.groupby('Disney Kanal').sum().round(2)[['Media Budget n/n/-','est. Ad Impressions','est. Ad Clicks','est. Views']].reset_index(drop=False)
df_main['est. Ad Impressions'] = df_main['est. Ad Impressions'].apply(lambda x: int(x))
df_main['est. Ad Clicks'] = df_main['est. Ad Clicks'].apply(lambda x: int(x))

def top_channel(channel_name, feature):
    data = df.groupby(['Disney Kanal', 'Format', 'Publisher']).sum().round(2)[['Media Budget n/n/-']].sort_values('Media Budget n/n/-', ascending=False).reset_index()
    data_filter = data[data['Disney Kanal']==channel_name][feature].tolist()
    return '\n'.join(data_filter[:5])

def top_channel_view(channel_name):
    view_sum = df[(df['Disney Kanal']==channel_name)]['est. Views'].sum()
    return f"{int(view_sum) :,d}"


df_main['Format'] = df_main['Disney Kanal'].apply(lambda x: top_channel(x, 'Format'))
df_main['Top Platzierungen'] = df_main['Disney Kanal'].apply(lambda x: top_channel(x, 'Publisher'))
df_main['TKP'] = df_main.apply(lambda x: round((x['Media Budget n/n/-'] / (x['est. Ad Impressions'] / 1000)),2) if x['est. Ad Impressions'] > 0 else 0, axis=1) # TKP = Budget / (Impressions/1000)
df_main['Video Views'] = df_main['Disney Kanal'].apply(lambda x: top_channel_view(x))
df_main['Datenstrategie'] = len(df_main)*[""]
df_main['Gewichtung'] = df_main['Media Budget n/n/-'].apply(lambda x: x/(df_main['Media Budget n/n/-'].sum()))
df_main['Sichtbarkeit (Prognose)'] = len(df_main)*[""]
df_main['Sichtbarkeit (Benchmark)'] = len(df_main)*[""]
df_main['Cost per Video View'] = (df_main['Media Budget n/n/-'] / df_main['est. Views'])
df_main['Cost per Video View'] = df_main['Cost per Video View'].apply(lambda x:  x if str(x)!='inf' else 0)

tkp_weighted = round(sum(df_main['TKP'] * df_main['Media Budget n/n/-']) / sum(df_main['Media Budget n/n/-']),2)

## INFO BOX 
info_fields = [
    'LOB',
    'Kampagne',
    'Start',
    'Ende',
    'Laufzeit',
    'Budget',
    'Video Views',
    '?? CPV',
    '?? TKP'
]

info_values = [
    info_box_values[4],
    info_box_values[2],
    info_box_values[8].split('-')[0],
    info_box_values[8].split('-')[1],
    f"{days_between(info_box_values[8].split('-')[0], info_box_values[8].split('-')[1])} Tage",
    german_style(f"{round(float(handling_tech_fee+df_main['Media Budget n/n/-'].sum()),2):,} ???"),
    german_style(f"{int(df_sl_views) :,d}"),
    german_style(f"{round(df_main['Cost per Video View'].mean(),2) :,.2f} ???" ),
    german_style(f"{round(sum(df_main['TKP'] * df_main['Media Budget n/n/-']) / sum(df_main['Media Budget n/n/-']),2) :,.2f} ???" )
]

df_infobox = pd.DataFrame({'Rahmendaten': info_fields,
                           '': info_values
                          })

## MAIN TABLE CLEANUP
df_main = df_main[[
    'Disney Kanal', 
    'Gewichtung',
    'Format',
    'Top Platzierungen', 
    'Datenstrategie', 
    'Media Budget n/n/-', 
    'est. Ad Impressions',
    'TKP',
    'Video Views', 
    'Sichtbarkeit (Prognose)', 
    'Sichtbarkeit (Benchmark)',
    'Cost per Video View',
]]

df_main.rename(columns={
    'Disney Kanal':'Kanal',
    'Media Budget n/n/-':'Budget',
    'est. Ad Impressions':'Impressions'
    }, inplace=True)

# Main Table TOTALs
total_budget = german_style(f"{df_main['Budget'].sum().round(2) :,.2f} ???")
total_tkp = german_style(f"{tkp_weighted :,.2f} ???" )
total_cpvv = german_style(f"{df_main['Cost per Video View'].sum().round(2) :,.2f} ???" )
total_impressions = german_style(f"{int(df_main['Impressions'].sum()) :,d}")
total_lvv = german_style(f"{int(df_sl_views) :,d}" )
total_budget_fee = german_style(f"{round(df_main['Budget'].sum()+handling_tech_fee,2) :,} ???" )
handling_tech_fee = german_style(f"{round(handling_tech_fee,2) :,} ???" )

df_main['Budget'] = df_main['Budget'].apply(lambda x: german_style(f"{round(x,2) :,.2f} ???"))
df_main['TKP'] = df_main['TKP'].apply(lambda x: german_style(f"{round(x,2) :,.2f} ???"))
df_main['Impressions'] = df_main['Impressions'].apply(lambda x: german_style(f"{int(x) :,d}"))
df_main['Cost per Video View'] = df_main['Cost per Video View'].apply(lambda x: german_style(f"{round(x,2) :,.2f} ???"))


###############################
######## CREATE EXCEL #########
###############################

writer = pd.ExcelWriter(output_dir, engine='xlsxwriter')

# INFO BOX
df_infobox.to_excel(writer, sheet_name='Mediaplan Abstract', startcol=0, startrow=6)

# SET workbook
workbook = writer.book
worksheet = writer.sheets['Mediaplan Abstract']

# INSERT IMAGE
worksheet.insert_image('B2', 'webapp/static/disneylogo.png')

# HIDE GRIDLINES
worksheet.hide_gridlines(option=2)

## FORMAT
format_header = workbook.add_format({'bold': True, 'font_color': 'white', 'bg_color':'black'})
format_header_2 = workbook.add_format({'bold': True, 'font_color': 'white', 'bg_color':'black'})
format_header_2.set_align('vcenter')
format_header_2.set_text_wrap()
format_total = workbook.add_format({'bold': True, 'font_color': 'white', 'bg_color':'black', 'align': 'right'})
format_subtotal_header = workbook.add_format({'bold': True, 'font_color': 'white', 'bg_color':'#808080', 'align': 'left'})
format_subtotal_header.set_align('vcenter')
format_subtotal = workbook.add_format({'bold': True, 'font_color': 'white', 'bg_color':'#808080', 'align': 'right'})

format_row_border = workbook.add_format()
format_row_border.set_border()
format_row_border.set_top_color('white')
format_row_border.set_bottom_color('black')
format_row_border.set_left_color('white')
format_row_border.set_right_color('white')
format_row_border.set_align('vcenter')
format_row_border.set_text_wrap()

format_row_border_kanal = workbook.add_format({'valign': 'vcenter'})
format_row_border_kanal.set_border()
format_row_border_kanal.set_top_color('white')
format_row_border_kanal.set_bottom_color('black')
format_row_border_kanal.set_left_color('white')
format_row_border_kanal.set_right_color('white')
format_row_border_kanal.set_bold()

format_string = workbook.add_format({'align': 'right', 'valign': 'vcenter'})
format_string.set_border()
format_string.set_top_color('white')
format_string.set_bottom_color('black')
format_string.set_left_color('white')
format_string.set_right_color('white')

format_row_border_perc = workbook.add_format({'num_format': '0%', 'valign': 'vcenter'})
format_row_border_perc.set_border()
format_row_border_perc.set_top_color('white')
format_row_border_perc.set_bottom_color('black')
format_row_border_perc.set_left_color('white')
format_row_border_perc.set_right_color('white')
format_row_border_perc.set_align('center')

merge_format = workbook.add_format({'valign': 'center'})
merge_format.set_border()
merge_format.set_top_color('white')
merge_format.set_bottom_color('black')
merge_format.set_left_color('white')
merge_format.set_right_color('white')
merge_format.set_align('vcenter')
merge_format.set_text_wrap()

worksheet.write('B7', 'Rahmendaten', format_header)
worksheet.write('C7', None, format_header)
    
# MAIN DATA    
main_columns = df_main.columns
for i, column_header in enumerate(main_columns):
    worksheet.write(f'{abc[i+1]}25', column_header, format_header_2)
    
    for j, values in enumerate(df_main[column_header].tolist()):
        if column_header in ['Budget','TKP','Cost per Video View']:
            worksheet.write(f'{abc[i+1]}{j+1+25}', values, format_string) 
        elif column_header == 'Gewichtung': 
            worksheet.write(f'{abc[i+1]}{j+1+25}', values, format_row_border_perc)
        elif column_header == 'Kanal': 
            worksheet.write(f'{abc[i+1]}{j+1+25}', values, format_row_border_kanal)
        elif column_header in ['Impressions','Video Views']:
            worksheet.write(f'{abc[i+1]}{j+1+25}', values, format_string)
        else:
            worksheet.write(f'{abc[i+1]}{j+1+25}', values, format_row_border)
        
        if j+1 == len(df_main):
            worksheet.write(f'{abc[i+1]}{j+2+25}', " ", format_subtotal)
            worksheet.write(f'{abc[i+1]}{j+3+25}', " ", format_total)

# SUBTOTAL TOTAL            
worksheet.write(f'B{len(df_main)+1+25}', "Handling & Tech-Fee", format_subtotal_header)
worksheet.write(f'B{len(df_main)+2+25}', "GESAMT", format_total)

data_stretey_value = '\n'.join([i[:25] for i in data_strategy.Datenstrategie.tolist()])
worksheet.merge_range(f'F26:F{len(df_main)+25}', data_stretey_value, merge_format)

# Budget
worksheet.write(f'G{len(df_main)+1+25}', handling_tech_fee, format_subtotal)
worksheet.write(f'G{len(df_main)+2+25}', total_budget_fee, format_total)
# Impressions | 
worksheet.write(f'H{len(df_main)+2+25}', total_impressions, format_total)
worksheet.write(f'I{len(df_main)+2+25}', total_tkp, format_total)
worksheet.write(f'J{len(df_main)+2+25}', total_lvv, format_total)
worksheet.write(f'M{len(df_main)+2+25}', total_cpvv, format_total)


# COLUMN WIDTH
row, cols = df_main.shape
columns = ["     "]+df_main.columns
for col_nb in range(cols+1):
    if col_nb in [3,4,5]:
        worksheet.set_column(col_nb, col_nb, 34)
    elif col_nb in [2]:
        worksheet.set_column(col_nb, col_nb, 28)
    else:    
        worksheet.set_column(col_nb, col_nb, 18)
    
# First Column
worksheet.set_column(0, 0, 4)
for i in range(50):
    worksheet.write(f'A{i}', " " )    

#########
## VIZ ##
#########

# BUDGET
graph_budget.to_excel(writer, sheet_name='data', startcol=0, startrow=0)
        
# SET workbook
workbook = writer.book
worksheet2 = writer.sheets['data']

graph_budget_format = workbook.add_format({'num_format': '#,##0'})
graph_perc = workbook.add_format({'num_format': '0%'})

for row_nb, value in enumerate(graph_budget.Budget.tolist()):
    worksheet2.write(row_nb+1, 2, value, graph_budget_format)

chart_budget = workbook.add_chart({'type': 'column'})
chart_budget.add_series({
    'categories': f'=data!$B$2:$B${len(graph_budget)+1}',
    'values':     f'=data!$C$2:$C${len(graph_budget)+1}',
    'gap':        2,
    'fill':   {'color': '#4285F4'}
})

chart_budget.set_chartarea({
    'border': {'none': True},
    'fill': {'none': True},
})

chart_budget.set_x_axis({'name': 'Tag'})
chart_budget.set_y_axis({'name': 'Budget in ???', 'major_gridlines': {'visible': False}})
chart_budget.set_title({'name': 'Werbedruck'})
chart_budget.set_legend({'position': 'none'})

# # Insert the chart into the worksheet.
worksheet.insert_chart('D7', chart_budget)

# DEVICE
graph_device.to_excel(writer, sheet_name='data', startcol=5, startrow=0)

for row_nb, value in enumerate(graph_device.Share.tolist()):
    worksheet2.write(row_nb+1, 7, value, graph_perc)

chart_device = workbook.add_chart({'type': 'column'})
chart_device.add_series({
    'categories': f'=data!$G$2:$G${len(graph_device)+1}',
    'values':     f'=data!$H$2:$H${len(graph_device)+1}',
    'gap':        2,
    'fill':   {'color': '#4285F4'}
})

chart_device.set_chartarea({
    'border': {'none': True},
    'fill': {'none': True},
})

chart_device.set_x_axis({'name': 'Device'})
chart_device.set_y_axis({'name': 'Share %', 'major_gridlines': {'visible': False}})
chart_device.set_title({'name': 'Devices'})
chart_device.set_legend({'position': 'none'})

# # Insert the chart into the worksheet.
worksheet.insert_chart('F7', chart_device)


# STRATEGY
zielgrp.to_excel(writer, sheet_name='data', startcol=10, startrow=0)

for row_nb, value in enumerate(zielgrp.Share.tolist()):
    worksheet2.write(row_nb+1, 12, value, graph_perc)
    
chart_strategy = workbook.add_chart({'type': 'pie'})
chart_strategy.add_series({
    'categories': f"='data'!$L$2:$L${len(zielgrp)+1}",
    'values':     f"='data'!$M$2:$M${len(zielgrp)+1}",
    # 'gap':        2,
    # 'fill':   {'color': '#4285F4'}
})

# chart_strategy.set_style(10)
chart_strategy.set_chartarea({
    'border': {'none': True},
    'fill': {'none': True},
})

chart_strategy.set_x_axis({'name': 'Zielgruppe'})
chart_strategy.set_y_axis({'name': 'Share %', 'major_gridlines': {'visible': False}})
chart_strategy.set_title({'name': 'Budget pro Zielgruppe'})

# # Insert the chart into the worksheet.
worksheet.insert_chart('I7', chart_strategy)

# Kanal
df_channel.to_excel(writer, sheet_name='data', startcol=15, startrow=0)

for row_nb, value in enumerate(df_channel.Share.tolist()):
    worksheet2.write(row_nb+1, 17, value, graph_perc)

chart_channel = workbook.add_chart({'type': 'column'})
chart_channel.add_series({
    'categories': f'=data!$Q$2:$Q${len(df_channel)+1}',
    'values':     f'=data!$R$2:$R${len(df_channel)+1}',
    'gap':        2,
    'fill':   {'color': '#4285F4'}
})

chart_channel.set_chartarea({
    'border': {'none': True},
    'fill': {'none': True},
})

chart_channel.set_x_axis({'name': 'Kanal'})
chart_channel.set_y_axis({'name': 'Share %', 'major_gridlines': {'visible': False}})
chart_channel.set_title({'name': 'Kan??le'})
chart_channel.set_legend({'position': 'none'})

# # Insert the chart into the worksheet.
worksheet.insert_chart('M7', chart_channel)

# SAVE EXCEL
writer.save()

