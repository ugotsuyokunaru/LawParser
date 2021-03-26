import time
from datetime import datetime, timedelta, date
import os
import json
import csv
import sys
import traceback
import argparse

import numpy as np
import pandas as pd
from PIL import Image
import pytesseract
# pytesseract.pytesseract.tesseract_cmd = './tesseract-ocr-w64-setup-v5.0.0-alpha.20201127.exe'  # 指定安裝軟體的位置

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.action_chains import ActionChains
from ipdb import set_trace

from mapping import city_map, city_list, type_list, shape_map, floor_map, facility_map, other_map


def parse_verification_img(img):
    img_str = pytesseract.image_to_string(img)
    # print('origin_parsed_img_str : {}'.format(img_str))
    img_str_split = img_str.split('\n')[0]
    # print('splited_img_str : {}'.format(img_str_split))
    print(img_str_split)
    return img_str_split

def screenshot_crop_code(driver, img_path):
    img = driver.find_element_by_xpath('//img[@id="captchaImage"]')
    time.sleep(1)
    location = img.location
    size = img.size

    left = location['x']
    top = location['y']
    right = left + size['width']
    bottom = top + size['height']

    # left = 2 * location['x']
    # top = 2 * location['y']
    # right = left + 2 * size['width'] - 10
    # bottom = top + 2 * size['height'] - 10

    driver.save_screenshot('./tmp_img/screenshot.png')
    page_snap_obj = Image.open('./tmp_img/screenshot.png')
    image_obj = page_snap_obj.crop((left, top, right, bottom))
    image_obj.save(img_path)

def loop_get_valid_code(browser, main_url, img_path):
    not_valid_yet = True

    while not_valid_yet:
        browser.get(main_url)
        screenshot_crop_code(browser, img_path=img_path)
        img = Image.open(img_path)
        verification_code = parse_verification_img(img)
        try:
            verification_code_num = int(verification_code)
            if 1 <= (verification_code_num / 10000) < 10:
                print('detect code success !!! (correct code = {})'.format(verification_code))
                not_valid_yet = False
            else:
                not_valid_yet = True
                print('detect code failure ... (wrong code = {})'.format(verification_code))
        except Exception as e:
            print('detect code failure ... (wrong code = {})'.format(verification_code))
            # print(e)
            # error_class = e.__class__.__name__ #取得錯誤類型
            # detail = e.args[0] #取得詳細內容
            # cl, exc, tb = sys.exc_info() #取得Call Stack
            # lastCallStack = traceback.extract_tb(tb)[-1] #取得Call Stack的最後一筆資料
            # fileName = lastCallStack[0] #取得發生的檔案名稱
            # lineNum = lastCallStack[1] #取得發生的行號
            # funcName = lastCallStack[2] #取得發生的函數名稱
            # errMsg = "File \"{}\", line {}, in {}: [{}] {}".format(fileName, lineNum, funcName, error_class, detail)
            # print(errMsg)
            not_valid_yet = True
            time.sleep(3)
    
    return verification_code

def fill_in_opt(browser, fy1, fy2, fm1, fm2, fd1, fd2):
    # (1) select cities
    # cities_list = ['...', '...']

    print('Filled in [{}-{}-{}({}) ~ {}-{}-{}({})]\n'.format(
        fy1, fm1, fd1, int(fy1)+1911, 
        fy2, fm2, fd2, int(fy2)+1911)
    )

    # (1) select all cities
    option_buttons = browser.find_element_by_class_name('form-control')
    for option in option_buttons.find_elements_by_tag_name('option'):
        option.click()
        # if option.text in cities_list:
        #     option.click()

    # (2) fill in date range
    Select(browser.find_element_by_id('fy1')).select_by_value(fy1)
    Select(browser.find_element_by_id('fy2')).select_by_value(fy2)
    Select(browser.find_element_by_id('fm1')).select_by_value(fm1)
    Select(browser.find_element_by_id('fm2')).select_by_value(fm2)
    Select(browser.find_element_by_id('fd1')).select_by_value(fd1)
    Select(browser.find_element_by_id('fd2')).select_by_value(fd2)

def main_parse(fy1, fy2, fm1, fm2, fd1, fd2, save_root):
    # 利用chrome模擬器開啟
    browser = webdriver.Chrome('./chromedriver')
    main_url = "https://psue.moj.gov.tw/psiqs"
    img_path = './tmp_img/validcode.png'
    os.makedirs('./tmp_img/', exist_ok=True)
    os.makedirs('./{}/'.format(save_root), exist_ok=True)
    columns = ["序號", "偵查案號", "偵結日期", "案由", "類別", "裁判日期", "裁判案號"]

    # verification_code = loop_get_valid_code(browser, main_url, img_path)
    browser.get(main_url)

    not_yet_verify = True
    while not_yet_verify:
        try:
            # (3) get verification code
            verification_code = loop_get_valid_code(browser, main_url, img_path)
            # (4) fill in options
            fill_in_opt(browser, fy1, fy2, fm1, fm2, fd1, fd2)
            # (5) fill in validcode
            browser.find_element_by_id('inputCaptcha').send_keys(verification_code)
            # (6) submit
            submit = browser.find_element_by_xpath("//input[@type='submit']")
            submit.click()
            time.sleep(3)

            print('success till here 1')

            FatFooter = browser.find_element_by_id('FatFooter')
            foot = FatFooter.find_elements_by_xpath("//nav/ul")[0]
            lis = foot.find_elements_by_xpath("li")
            location_num = len(lis)

            print('success till here 2')

            not_yet_verify = False
        except Exception as e:
            print('entered wrong code ... (wrong code = {})'.format(verification_code))
            print(e)
            error_class = e.__class__.__name__ #取得錯誤類型
            detail = e.args[0] #取得詳細內容
            cl, exc, tb = sys.exc_info() #取得Call Stack
            lastCallStack = traceback.extract_tb(tb)[-1] #取得Call Stack的最後一筆資料
            fileName = lastCallStack[0] #取得發生的檔案名稱
            lineNum = lastCallStack[1] #取得發生的行號
            funcName = lastCallStack[2] #取得發生的函數名稱
            errMsg = "File \"{}\", line {}, in {}: [{}] {}".format(fileName, lineNum, funcName, error_class, detail)
            print(errMsg)
            not_yet_verify = True
            time.sleep(1)

    print('\nStart parsing ...\n')
    for ind in range(location_num):
        # (1) select location

        # 因為 click 後，html 會重新刷新，所以每次要重新 find element
        FatFooter = browser.find_element_by_id('FatFooter')
        foot = FatFooter.find_elements_by_xpath("//nav/ul")[0]
        lis = foot.find_elements_by_xpath("li")
        cities_num = len(lis)
        
        loc_text = lis[ind].text
        loc_text_root = loc_text.split('(')[0]
        loc_num = loc_text.split('(')[1].split(')')[0]
        csv_folder = os.path.join(save_root, loc_text_root)
        csv_path = os.path.join(csv_folder, '{:03}{:02}{:02}_{:03}{:02}{:02}_{}.csv'.format(
            int(fy1), int(fm1), int(fd1), int(fy2), int(fm2), int(fd2), loc_num)
        )
        if os.path.isfile(csv_path):
            print('[{}/{}]: {} already existed, skip this.'.format(ind+1, cities_num, loc_text))
        else:
            print('[{}/{}]: {} not downloaded yet, start parsing.'.format(ind+1, cities_num, loc_text))
            os.makedirs(csv_folder, exist_ok=True)
            lis[ind].click()
            time.sleep(1)

            # get data num
            # '查詢結果共285356筆(基隆地檢共6095筆， 只顯示前500筆， 目前顯示第21 ~ 40筆)'
            # '查詢結果共203筆(臺北地檢共77筆， 目前顯示第1 ~ 20筆)'
            target_text = browser.find_element_by_class_name('Items').text 
            total_num = int(target_text.split('地檢共')[1].split('筆， ')[0])
            exceed_500 = False
            final_page = False
            if total_num > 500:
                total_num = 500
                exceed_500 = True
            # data_num = int(target_text.split('只顯示前')[1].split('筆， 目前顯示')[0])
            current_num = 0
            current_num_delta = 20  # design for web bug : record and real data not aligned

            data_list_by_location = []

            while (current_num < total_num):
                # (2) parse info (section class="listTb")
                # 因為 click 後，html 會重新刷新，所以每次要重新 find element

                # [序號, 偵查案號, 偵結日期, 案由, 類別, 裁判日期, 裁判案號, ...]
                # 7 個一組，共 20 筆 data
                # len(table_data_list) = 140 (20 row x 7 col)

                if final_page:
                    break

                table_data_list = browser.find_elements_by_xpath("//tbody/tr/td")
                # current_num += int(len(table_data_list)/7) # >> wrong ...
                current_num = int(table_data_list[-7].text)
                current_num_small = int(table_data_list[0].text)
                current_num_delta = (current_num - current_num_small) + 1
                if (current_num_delta < 20):
                    final_page = True
                print('\tparsing {} ...'.format(current_num))

                for idx, item in enumerate(table_data_list):
                    if idx % 7 == 0:
                        if idx == 7:
                            data_list_by_location.append(tmp_list)
                        elif idx != 0:
                            if data_list_by_location[-1][0] != tmp_list[0]:
                                data_list_by_location.append(tmp_list)
                            else:
                                print('\t[Website Bug: duplicated parsing] {} <=> {}'.format(data_list_by_location[-1][0], tmp_list[0]))
                        tmp_list = [item.text]
                    else:
                        tmp_list.append(item.text)
                        if idx == (len(table_data_list)-1):
                            data_list_by_location.append(tmp_list)

                # (3) select next page (div class="Pagination text-center")
                page_buttons = browser.find_element_by_class_name("pagination")
                next_buttons = page_buttons.find_elements_by_xpath("li/a/span")
                for button in next_buttons:
                    if button.text == '»':
                        button.click()
                        break
                # if next_buttons[-2].text == '+10頁': # max total = 6
                #     if len(next_buttons) == 6: # [第一頁 /-10頁 / « /  ...   / » / +10頁 / 最後一頁]
                #         next_ind = 3
                #     elif len(next_buttons) in [4, 5]:
                #         next_ind = 2
                #     else:
                #         next_ind = None # not handle bug
                # else:   # max total = 5
                #     if len(next_buttons) == 5: # [第一頁 /-10頁 / « /  ...   / » / 最後一頁]
                #         next_ind = 3
                #     elif len(next_buttons) in [3, 4]:
                #         next_ind = 2
                #     else:
                #         next_ind = None # not handle bug                
                # next_buttons[next_ind].click()
                time.sleep(1)

            print('\tparsing finished, saving file ... ')
            df_by_loc = pd.DataFrame(data_list_by_location, columns=columns)
            df_by_loc.to_csv(csv_path, index=False)
            if exceed_500:
                with open('csv_exceed_500.txt', 'a') as file:
                    file.write('{}\n'.format(csv_path))

    browser.close()
    print('\nfinish!')

def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument('--fy1', default=107, type=int, choices=range(85, 110+1))
    parser.add_argument('--fy2', default=109, type=int, choices=range(85, 110+1))
    parser.add_argument('--fm1', default=7, type=int, choices=range(1, 12+1))
    parser.add_argument('--fm2', default=12, type=int, choices=range(1, 12+1))
    parser.add_argument('--fd1', default=1, type=int, choices=range(1, 31+1))
    parser.add_argument('--fd2', default=31, type=int, choices=range(1, 31+1))

    args = parser.parse_args()
    return args

if __name__ == '__main__':
    # 107/7/1 到 109/12/31
    args = parse_args()

    fy1 = str(args.fy1)
    fm1 = str(args.fm1)
    fd1 = str(args.fd1)

    fy2 = str(args.fy2)
    fm2 = str(args.fm2)
    fd2 = str(args.fd2)

    save_root = '{:03}{:02}{:02}_{:03}{:02}{:02}'.format(int(fy1), int(fm1), int(fd1), int(fy2), int(fm2), int(fd2)) # '1070701_1092131'

    print('\tTotal Date Range in [{}-{}-{}({}) ~ {}-{}-{}({})]\n'.format(
        fy1, fm1, fd1, int(fy1)+1911, 
        fy2, fm2, fd2, int(fy2)+1911)
    )

    start_date = date(int(fy1)+1911, int(fm1), int(fd1))
    end_date = date(int(fy2)+1911, int(fm2), int(fd2))
    week_delta = timedelta(weeks=1)
    delta_num = int((end_date - start_date) / week_delta) + 1
    current_delta_num = 1
    
    current_date = start_date
    next_date = current_date + week_delta
    current_y = fy1
    current_m = fm1
    current_d = fd1
    next_y = str(next_date.year - 1911)
    next_m = str(next_date.month)
    next_d = str(next_date.day)
    parse_success = True

    error_date = end_date
    err_count = 0

    while (end_date - next_date).days > 0:
        if (current_date == error_date) and (err_count > 5):
            # skip this date (some unknown errors might occur)
            print('\t\t[Skip this date : Error count = {} (error_date = {}]'.format(err_count, error_date))
            # update
            current_date = next_date
            next_date = current_date + week_delta
            current_y = str(current_date.year - 1911)
            current_m = str(current_date.month)
            current_d = str(current_date.day)
            next_y = str(next_date.year - 1911)
            next_m = str(next_date.month)
            next_d = str(next_date.day)
            current_delta_num += 1
            err_count = 0
            print('\t\t[Skiped, new date = {}]'.format(err_count, current_date))
        else:
            try:
                print('\n[{} / {}] Start parsing !!!'.format(current_delta_num, delta_num))
                print('\tDate Range in [{}-{}-{}({}) ~ {}-{}-{}({})]\n'.format(
                    current_y, current_m, current_d, int(current_y)+1911, 
                    next_y, next_m, next_d, int(next_y)+1911)
                )

                main_parse(current_y, next_y, current_m, next_m, current_d, next_d, save_root)

                # update
                current_date = next_date
                next_date = current_date + week_delta
                current_y = str(current_date.year - 1911)
                current_m = str(current_date.month)
                current_d = str(current_date.day)
                next_y = str(next_date.year - 1911)
                next_m = str(next_date.month)
                next_d = str(next_date.day)
                current_delta_num += 1
            except Exception as e:
                print('parsing failed ... / try again after 10 seconds ...')
                print(e)
                error_class = e.__class__.__name__ #取得錯誤類型
                detail = e.args[0] #取得詳細內容
                cl, exc, tb = sys.exc_info() #取得Call Stack
                lastCallStack = traceback.extract_tb(tb)[-1] #取得Call Stack的最後一筆資料
                fileName = lastCallStack[0] #取得發生的檔案名稱
                lineNum = lastCallStack[1] #取得發生的行號
                funcName = lastCallStack[2] #取得發生的函數名稱
                errMsg = "File \"{}\", line {}, in {}: [{}] {}".format(fileName, lineNum, funcName, error_class, detail)
                print(errMsg)
                time.sleep(10)

                error_date = current_date
                err_count += 1
                print('\t\t[Error count = {} (error_date = {}]'.format(err_count, error_date))
