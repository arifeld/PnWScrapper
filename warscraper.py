# -*- coding: utf-8 -*-
"""
A project that webscrapes the PnW website to produce a Google spreadsheet that sorts people by their active wars.
"""

import gspread
from gspread_formatting import *
from oauth2client.service_account import ServiceAccountCredentials

import requests
import urllib.request
import time
from bs4 import BeautifulSoup
import re

friendlyAlliance = "Dark Brotherhood"

scope = ['https://spreadsheets.google.com/feeds',
         'https://www.googleapis.com/auth/drive']
credentials = ServiceAccountCredentials.from_json_keyfile_name('pnw-webscraper-39e5c239e9f6.json', scope)
gc = gspread.authorize(credentials)


#testDocument = gc.create("GoG Friendly War List")
#testDocument.share("feldma2002@gmail.com", perm_type="user", role="owner")

# For now, we are going to be editing the same spreadsheet.
# Let's start with the basic information / table setup:
sh = gc.open("GoG War List (Auto Generated)")
worksheet = sh.get_worksheet(0)
worksheet.resize(2000, 50)

allianceURL = input("URL of alliance member list? ")
allianceURL2 = input("URL of alliance member list page 2. ")

useSecure = bool(input("Use secure connection? True if yes, False if no. "))
#allianceURL = "https://politicsandwar.com/index.php?id=15&memberview=true&keyword=dark+brotherhood&cat=alliance&ob=score&od=DESC&maximum=53&minimum=0&search=Go"
# Get the first 100 nations in the alliance. Use a set to ensure only unique values are set.
nationLinks = set()
allianceRequest = requests.get(allianceURL, verify=useSecure)
allianceSoup = BeautifulSoup(allianceRequest.text, "html.parser")
testIndex = 1
for link in allianceSoup.find_all("a"):
    linkhref = link.get("href")
    if (linkhref.find("nation") != -1 and linkhref.find("id") != -1):
        testIndex += 1
        nationLinks.add(linkhref)


# Do it again.
allianceRequest1 = requests.get(allianceURL2, verify=useSecure)
allianceSoup1 = BeautifulSoup(allianceRequest1.text, "html.parser")
for link in allianceSoup1.find_all("a"):
    linkhref = link.get("href")
    if (linkhref.find("nation") != -1 and linkhref.find("id") != -1):
        testIndex += 1
        nationLinks.add(linkhref)


print("TESTING OVER")
print(len(nationLinks))
allWars = {}
logIndex = 1
for nationURL in nationLinks:
    print("(" + str(logIndex) + " - " + str(round(((logIndex/len(nationURL)))*100, 2)) + "%) " + nationURL)
    logIndex += 1
    nationRequest = requests.get(nationURL + "&display=war", verify=False)
    nationSoup = BeautifulSoup(nationRequest.text, "html.parser")
    # grab the nation table.

    allWarInfo = []
    for value in nationSoup.find_all("tr"):
        singleWarInfo = []
        if value.find("th") != None: continue # gets rid of the date column
        for string in value.stripped_strings:
            singleWarInfo.append(string)
        allWarInfo.append(singleWarInfo)
    
    for warInfo in allWarInfo:
        if (warInfo[0] == "No wars to display"): continue 
        if warInfo[-2] == "Active War":
            enemy = ""
            # check which person is from the other alliance.
            if (warInfo[4] == friendlyAlliance):
                enemy = (warInfo[6], warInfo[7])
                friend = (warInfo[3], warInfo[4])
            else:
                if (warInfo[7] == friendlyAlliance): # check if the other person is actually from DB
                    enemy = (warInfo[3],  warInfo[4])
                else: # they aren't, so mark it.
                    enemy = (warInfo[3] + " (Not in DB)", warInfo[4])
                
                friend = warInfo[6], warInfo[7]

            # Add value to the table.
            if enemy in allWars:
                if (friend in allWars[enemy]): # this shouldn't happen?
                    print("ERROR REPORTING: " + str(friend))
                    print("\n")
                    continue
                else:
                    allWars[enemy].append(friend)
            else:
                allWars[enemy] = [friend]
                
print(allWars)

# We can now update all our data:
# Title:
rowTitles = ["ENEMY NAME", "ENEMY ALLIANCE", "ALLY NAME", "ALLY ALLIANCE"]
cell_list = worksheet.range('B2:E2')
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
format_cell_range(worksheet, 'B2:E2', titleFormat)

rowIndex = 3
# We will leave 8 slots per aggressor, and fill in each one as required.
cellObjects = []
for attacker in allWars: #attacker is the key value.
    for i in range(len(allWars[attacker])):
        cellObjects.append(gspread.models.Cell(rowIndex+i, 2, value=attacker[0]))
        cellObjects.append(gspread.models.Cell(rowIndex+i, 3, value=attacker[1]))
        cellObjects.append(gspread.models.Cell(rowIndex+i, 4, value=allWars[attacker][i][0]))
        cellObjects.append(gspread.models.Cell(rowIndex+i, 5, value=allWars[attacker][i][1]))
    
    # i shouldn't go greater than 8, so let's add 9 to rowIndex.
    rowIndex += (i+1)

# update all the cells at once.
worksheet.update_cells(cellObjects, "USER_ENTERED")

# General format
generalFormat = cellFormat(horizontalAlignment = "CENTER", wrapStrategy = "WRAP", borders={
            "top": borderFormat,
            "bottom": borderFormat,
            "left": borderFormat,
            "right": borderFormat})
    
format_cell_range(worksheet, "B2:E" + str(rowIndex), generalFormat)
    

