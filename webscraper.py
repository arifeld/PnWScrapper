# -*- coding: utf-8 -*-
print("Running!")
# Google spreadsheet imports.
import gspread
from gspread_formatting import *
from oauth2client.service_account import ServiceAccountCredentials

# Webscraping imports.
import requests
import urllib.request
import time
from bs4 import BeautifulSoup
import re

def projectCellFormat(info, index):
    # Green cell for "has this project"
    greenFormat = cellFormat(backgroundColor={"green": 1})
    # Red cell for "does not have this project"
    redFormat = cellFormat(backgroundColor = {"red": 1})
    return greenFormat if info[index] else redFormat
            

# Authorise to the Google API
scope = ['https://spreadsheets.google.com/feeds',
         'https://www.googleapis.com/auth/drive']
credentials = ServiceAccountCredentials.from_json_keyfile_name('pnw-webscraper-39e5c239e9f6.json', scope)
gc = gspread.authorize(credentials)


#testDocument = gc.create("GoG Statistics")
#testDocument.share("feldma2002@gmail.com", perm_type="user", role="owner")

# For now, we are going to be editing the same spreadsheet.
# Let's start with the basic information / table setup:
sh = gc.open("GoG Statistics v2")
worksheet = sh.get_worksheet(0)

# Create a table of values that we want to set, so we can do a batch job.
rowTitles = ["NATION NAME", "NATION LINK", "NATION SCORE", "WAR POLICY", "MAX INFRA", "AVG INFRA", "SOLDIERS", "TANKS", "AIRCRAFT", "SHIPS", "IA", "ID", "MLP", "NRF", "PB", "VDS"]
cell_list = worksheet.range('B2:Q2')
iterativeIndex = 0
for cell in cell_list:
    cell.value = rowTitles[iterativeIndex]
    iterativeIndex += 1

borderFormat = { "style": "SOLID"}
titleFormat = cellFormat(
        horizontalAlignment='CENTER',
        borders={
                "top": borderFormat,
                "bottom": borderFormat,
                "left": borderFormat,
                "right": borderFormat
                },
        padding={
                "top": 5,
                "bottom": 5,
                "left": 15,
                "right": 15})
    
worksheet.update_cells(cell_list)
format_cell_range(worksheet, 'B2:Q2', titleFormat)

# Now we get to the fun bit - iterating over lots of data.

# Alliance URL
allianceURL = input("URL of alliance member list #1. ")
allianceURL2 = input("URL of alliance member list #2. ")
#allianceURL = "https://politicsandwar.com/index.php?id=15&memberview=true&keyword=dark+brotherhood&cat=alliance&ob=score&od=DESC&maximum=53&minimum=0&search=Go"
allianceRequest = requests.get(allianceURL)
allianceSoup = BeautifulSoup(allianceRequest.text, "html.parser")

allianceRequest2 = requests.get(allianceURL2)
allianceSoup2 = BeautifulSoup(allianceRequest.text, "html.parser")

nationLinks = set()
for link in allianceSoup.find_all("a"):
    linkhref = link.get("href")
    if (linkhref.find("nation") != -1 and linkhref.find("id") != -1):
        nationLinks.add(linkhref)
        
for link in allianceSoup2.find_all("a"):
    linkhref = link.get("href")
    if (linkhref.find("nation") != -1 and linkhref.find("id") != -1):
        nationLinks.add(linkhref)
        
rowIndex = 3
for nationURL in nationLinks:
    # Request the nation URL.
    nationRequest = requests.get(nationURL,verify=False)
    #BeautifulSoup the request, so we can deal with it.
    nationSoup = BeautifulSoup(nationRequest.text, "html.parser")
    print("DEBUG: Soup made")
    
    # Lists that will store information.
    currentNationInfo = [] # complete table
    infraInfo = [0, 0, 0] #maxinfra, totalinfra, # of cities.
    projectList = [False, False, False, False, False, False] #IA, ID, MLP, NRF, PB, VDS
    
    
    completeList = [] # there are two nationtable tables, so we need to add them.
    possiblevalues = nationSoup.find_all("table", class_="nationtable")
    for table in possiblevalues:
        completeList.append(table.find_all("tr"))
    
    
        
    saveInfo = False
    saveInfraInfo = False
    correctInfraInfo = True
    for table in completeList:
        for tableval in table:
            for string in tableval.stripped_strings:
                if (saveInfo):
                    currentNationInfo.append(string)
                    saveInfo = False
                if (re.search(r'\bNation Name:|\bNation Score:|\bWar Policy:|\bKilled:|\bDestroyed:|\bEaten:|\bMap', string) and string != "Infrastructure Destroyed:"):
                    saveInfo = True
                # Look for infra.
                if (saveInfraInfo):
                    # find the max infra level, have to remove the , from infra num though.
                    infraLevel = float(string.replace(r',',""))
                    infraInfo[0] = max(infraInfo[0], infraLevel)
                    
                    # add total infra info.
                    infraInfo[1] += infraLevel
                    infraInfo[2] += 1
                    saveInfraInfo = False
                if (re.search(r'\bInfra:', string)):
                    if correctInfraInfo:   
                        saveInfraInfo = True
                    # we need to alternate correctInfraInfo because it duplicates values.
                    correctInfraInfo = correctInfraInfo != True
                    
                # look for certain projects
                if ("Intelligence Agency" in string):
                    projectList[0]= True
                if ("Iron Dome" in string):
                    projectList[1] = True
                if ("Missile Launch Pad" in string):
                    projectList[2] = True
                if ("Nuclear Research Facility" in string):
                    projectList[3] = True
                if ("Propaganda Bureau" in string):
                    projectList[4] = True
                if ("Vital Defense System" in string):
                    projectList[5] = True
    
    # Add the infra level information to the currentNationInfo table.
    currentNationInfo.append(infraInfo[0])
    currentNationInfo.append(infraInfo[1]/infraInfo[2]) # average infra.
                
    print(currentNationInfo)
    
    # Let's add our data now.
    
    
    # General format
    generalFormat = cellFormat(horizontalAlignment = "CENTER", wrapStrategy = "WRAP", borders={
                "top": borderFormat,
                "bottom": borderFormat,
                "left": borderFormat,
                "right": borderFormat})
    
    cellInfoRange = worksheet.range("B" + str(rowIndex) + ":Q" + str(rowIndex))
    cellInfoIndex = 0
    for cell in cellInfoRange:
        # Lots of ifs, because python doesn't have a switch statement. :shrug:
        if (cellInfoIndex == 0): # nation name
            cell.value = currentNationInfo[0]
        elif (cellInfoIndex == 1): # nation link
            cell.value = '=HYPERLINK("' + nationURL + '", "Link")'
        elif (cellInfoIndex == 2): # nation score
            cell.value = currentNationInfo[1]
        elif (cellInfoIndex == 3): # nation policy
            cell.value = currentNationInfo[2]
        elif (cellInfoIndex == 4): # max infra
            cell.value = currentNationInfo[-2] # it's the second last value 
        elif (cellInfoIndex == 5): # average infra
            cell.value = currentNationInfo[-1]
        elif (cellInfoIndex == 6): # soldiers
            cell.value = currentNationInfo[3]
        elif (cellInfoIndex == 7): # tanks
            cell.value = currentNationInfo[4]
        elif (cellInfoIndex == 8): # aircraft
            cell.value = currentNationInfo[5]
        elif (cellInfoIndex == 9): # ships
            cell.value = currentNationInfo[6]
        #elif (cellInfoIndex == 10): #IA
           # format_cell_range(worksheet, gspread.utils.rowcol_to_a1(cell.row, cell.col), greenFormat if projectList[0] else redFormat)
        #elif (cellInfoIndex == 11): #ID
         #   format_cell_range(worksheet, gspread.utils.rowcol_to_a1(cell.row, cell.col), greenFormat if projectList[1] else redFormat)
        #elif (cellInfoIndex == 12): #MLP
         #   format_cell_range(worksheet, gspread.utils.rowcol_to_a1(cell.row, cell.col), greenFormat if projectList[2] else redFormat)    
        #elif (cellInfoIndex == 13): #NRF
         #   format_cell_range(worksheet, gspread.utils.rowcol_to_a1(cell.row, cell.col), greenFormat if projectList[3] else redFormat)
        #elif (cellInfoIndex == 14): #PB
         #   format_cell_range(worksheet, gspread.utils.rowcol_to_a1(cell.row, cell.col), greenFormat if projectList[4] else redFormat)    
        #elif (cellInfoIndex == 15): #VDS
         #   format_cell_range(worksheet, gspread.utils.rowcol_to_a1(cell.row, cell.col), greenFormat if projectList[5] else redFormat)
        # now highlight projects based on whether they have it or not.
        
        
        
        # finally, increment our index.
        cellInfoIndex += 1
    # Format project cells based on values.
    projectCellFormats = [
            ("L" + str(rowIndex), projectCellFormat(projectList, 0)), # IA
            ("M" + str(rowIndex), projectCellFormat(projectList, 1)), # ID
            ("N" + str(rowIndex), projectCellFormat(projectList, 2)), # MLP
            ("O" + str(rowIndex), projectCellFormat(projectList, 3)), # NRF
            ("P" + str(rowIndex), projectCellFormat(projectList, 4)), # PB
            ("Q" + str(rowIndex), projectCellFormat(projectList, 5)), # VDS
            ("B" + str(rowIndex) + ":Q" + str(rowIndex), generalFormat)
            ]
    worksheet.update_cells(cellInfoRange, "USER_ENTERED")
    format_cell_ranges(worksheet, projectCellFormats)
    rowIndex += 1
    

