#-*- coding: utf-8 -*-
import sys

import requests
import json
import pandas as pd
from datetime import date, datetime
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import requests
import dataframe_image as dfi
import os


pd.options.mode.chained_assignment = None

print(sys.getdefaultencoding())
TELEGRAM_TOKEN = os.environ['TELEGRAM_TOKEN']
MY_CHAT_ID = os.environ['MY_CHAT_ID']

BASE_URL = "https://api.telegram.org/bot{}".format(TELEGRAM_TOKEN)

def get_kospis(mydate:datetime):  # ouput is [kospi,kospi_200] in floats

  headers = {
      'Connection': 'keep-alive',
      'Accept': 'application/json, text/javascript, */*; q=0.01',
      'X-Requested-With': 'XMLHttpRequest',
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.61 Safari/537.36',
      'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
      'Origin': 'http://data.krx.co.kr',
      'Referer': 'http://data.krx.co.kr/contents/MDC/MDI/mdiLoader/index.cmd?menuId=MDC0201010104',
      'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
  }

  today_str = mydate.strftime('%Y%m%d')



  data = {
    'bld': 'dbms/MDC/STAT/standard/MDCSTAT00101',
    'idxIndMidclssCd': '02',
    'trdDd': today_str,
    'share': '2',
    'money': '3',
    'csvxls_isNo': 'false'
  }

  response = requests.post('http://data.krx.co.kr/comm/bldAttendant/getJsonData.cmd', headers=headers, data=data, verify=False).json()
  kospi = float(response['output'][1]['CLSPRC_IDX'].replace(",",""))
  kospi_200 = float(response['output'][2]['CLSPRC_IDX'].replace(",",""))
  return [kospi, kospi_200]

# 최근 옵션 만기일을 구하는 함수
# def get_recent_due(mydate:datetime)->datetime:

# monday is 0, thursday is 3
def nth_weekday(the_date, nth_week, week_day):
    temp = the_date.replace(day=1)
    adj = (week_day - temp.weekday()) % 7
    temp += timedelta(days=adj)
    temp += timedelta(weeks=nth_week-1)
    return temp

# test = nth_weekday(datetime(2021,9,10), 2, 3)

def get_recent_due(mydate:datetime)->datetime:
    # get 2nd thursday of the same month
    thismonth_duedate = nth_weekday(mydate, 2, 3)
    # in case today already passed the duedate (10/15) -> get nextmonth_duedate
    if mydate <= thismonth_duedate:
        return thismonth_duedate
    elif mydate > thismonth_duedate :
        nextmonth_duedate = nth_weekday(mydate+relativedelta(months=1),2, 3)
        return nextmonth_duedate

def get_raw_table(mydate:datetime):
    headers = {
        'Connection': 'keep-alive',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'X-Requested-With': 'XMLHttpRequest',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.61 Safari/537.36',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Origin': 'http://data.krx.co.kr',
        'Referer': 'http://data.krx.co.kr/contents/MDC/MDI/mdiLoader/index.cmd?menuId=MDC0201020101',
        'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
    }

    today_str = mydate.strftime('%Y%m%d')
    # today_str = '20211001'



    data = {
    'bld': 'dbms/MDC/STAT/standard/MDCSTAT12502',
    'trdDd': today_str,
    'prodId': 'KRDRVOPK2I',
    'trdDdBox1': today_str,
    'trdDdBox2': today_str,
    'mktTpCd': 'T',
    'rghtTpCd': 'T',
    'share': '1',
    'money': '3',
    'csvxls_isNo': 'false'
    }


    response = requests.post('http://data.krx.co.kr/comm/bldAttendant/getJsonData.cmd', headers=headers, data=data, verify=False).json()

    df = pd.json_normalize(response['output'])
    return df

def  get_call_table(mydate):
    df = get_raw_table(mydate)
        # get 6digit of recent due (if 20211014 -> 202110)
    mydue_str = get_recent_due(mydate).strftime('%Y%m')
    c_df = df[df['ISU_NM'].str.contains(f'C {mydue_str}', regex=False)]
    # 거래량과 미결제수량 합 구하기
    # 먼저 int로 바꾸기
    c_df['ACC_TRDVOL'] = c_df['ACC_TRDVOL'].str.replace(',', '').astype(int)
    c_df['ACC_OPNINT_QTY']= c_df['ACC_OPNINT_QTY'].str.replace(',', '').astype(int)
    c_df['SUM_TRD_OPN'] = c_df['ACC_TRDVOL']+ c_df['ACC_OPNINT_QTY']
    c_df['SUM_TRD_OPN']

    # get the 행사가
    c_df['STRIKE_PRICE'] = c_df['ISU_NM'].str[16:21].astype(float)

    # mydate = datetime(2021,10,1)

    # c_df['DIFF'] = abs(c_df['STRIKE_PRICE'] - get_kospis(mydate)[1])
    # c_df['DIFF']
    # sort by total and only display top three
    c_df = c_df.sort_values('SUM_TRD_OPN',ascending=False).head(3)

    ## get only the columns that I need
    # c_df = c_df[['STRIKE_PRICE','ACC_TRDVOL','ACC_OPNINT_QTY','SUM_TRD_OPN']]
    c_df = c_df[['STRIKE_PRICE','SUM_TRD_OPN']]


    ## change column name
    # c_df.columns = ['콜_행사가','콜_거래량','콜_미결제량','콜_수량합계']

    c_df.columns = ['콜_행사가','콜_수량합계']
    ## format 
    c_df.reset_index(drop=True, inplace=True)
    return c_df

def  get_put_table(mydate):
    df = get_raw_table(mydate)
        # get 6digit of recent due (if 20211014 -> 202110)
    mydue_str = get_recent_due(mydate).strftime('%Y%m')
    c_df = df[df['ISU_NM'].str.contains(f'P {mydue_str}', regex=False)]
    # 거래량과 미결제수량 합 구하기
    # 먼저 int로 바꾸기
    c_df['ACC_TRDVOL'] = c_df['ACC_TRDVOL'].str.replace(',', '').astype(int)
    c_df['ACC_OPNINT_QTY']= c_df['ACC_OPNINT_QTY'].str.replace(',', '').astype(int)
    c_df['SUM_TRD_OPN'] = c_df['ACC_TRDVOL']+ c_df['ACC_OPNINT_QTY']
    c_df['SUM_TRD_OPN']

    # get the 행사가
    c_df['STRIKE_PRICE'] = c_df['ISU_NM'].str[16:21].astype(float)

    # c_df['DIFF'] = abs(c_df['STRIKE_PRICE'] - get_kospis(mydate)[1])
    # c_df['DIFF']
    # sort by total and only display top three
    c_df = c_df.sort_values('SUM_TRD_OPN',ascending=False).head(3)

    ## get only the columns that I need
    c_df = c_df[['STRIKE_PRICE','SUM_TRD_OPN']]


    ## change column name

    c_df.columns = ['풋_행사가','풋_수량합계']
    ## format 

    c_df.reset_index(drop=True, inplace=True)
    return c_df

def get_final_table(mydate:datetime):
    df_c = get_call_table(mydate)
    df_p = get_put_table(mydate)

    newdf = pd.concat([df_c,df_p],axis=1)
    # define variables that will be used later on 
    call_sum = newdf['콜_수량합계'].sum()
    put_sum = newdf['풋_수량합계'].sum()
    strong_type = '콜' if call_sum > put_sum else '풋'
    kospi,kospi200 = get_kospis(mydate)
    mydate_str = mydate.strftime('%Y-%m-%d')

    # index of closest call,put indexes
    call_index = newdf.index[abs(newdf['콜_행사가'] - kospi200) == abs(newdf['콜_행사가'] - kospi200).min()].tolist()
    put_index = newdf.index[abs(newdf['풋_행사가'] - kospi200) == abs(newdf['풋_행사가'] - kospi200).min()].tolist()
    
    call_value = newdf.iloc[call_index]['콜_행사가'].values[0]
    put_value = newdf.iloc[put_index]['풋_행사가'].values[0]

    highlight_c = lambda x : ['color:red' if abs(x['콜_행사가'] - kospi200) == abs(newdf['콜_행사가'] - kospi200).min() else "" for i in x ]
    highlight_p = lambda x : ['color:red' if abs(x['풋_행사가'] - kospi200) == abs(newdf['풋_행사가'] - kospi200).min() else "" for i in x ]
    mystyler = newdf.style.apply(highlight_c,subset=['콜_행사가','콜_수량합계'],axis=1).apply(highlight_p,subset=['풋_행사가','풋_수량합계'],axis=1)

    mystyler = mystyler.format({'콜_행사가': "{:,.1f}",'콜_수량합계': "{:,.0f}",'풋_행사가': "{:,.1f}",'풋_수량합계': "{:,.0f}"}).hide_index()
    
    weekdays = ['월','화','수','목','금','토','일']

    recent_due = get_recent_due(mydate)
    recent_due_str = recent_due.strftime('%Y-%m-%d')
    num_of_remaining = recent_due - mydate
    mycaption = f"\
        {mydate_str}({weekdays[mydate.weekday()]}) 옵션현황<br>\
        - 코스피 / 코스피200 : {kospi} / {kospi200} <br>\
        - 유력 행사구간 : {put_value} ~ {call_value} <br>\
        - 다음 만기 ({recent_due_str}({weekdays[recent_due.weekday()]})) 까지 {num_of_remaining.days}일 남음<br>\
        - {strong_type} 우세"
    mystyler = mystyler.set_caption(mycaption)

    styles = [dict(selector="caption", 
    props=[("text-align", "left"),
    ("font-size", "100%"),
    ("color", 'gray')])]

    mystyler.set_table_styles(styles)
    dfi.export(mystyler,f"output.png")

def sendImage():
    url = BASE_URL + "/sendPhoto"
    files = {'photo': open("output.png", 'rb')}
    data = {'chat_id' : MY_CHAT_ID}
    r= requests.post(url, files=files, data=data)

# my main job -> 



def main():
    today = datetime.now()
    mydate = datetime(2021,10,1)
    get_final_table(mydate)
    sendImage()
    

if __name__ == "__main__":
	main()