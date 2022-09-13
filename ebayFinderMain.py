import json
import requests
from datetime import datetime
from datetime import timedelta
import smtplib
import ssl
import time

searchFreq = 15  # search frequency/how old items in minutes
searchKeyword = "fuji"
# searchKeyword = "(fuji,fujinon,fujifilm) 35 1.4"
searchMaxPrice = 3500
SearchEntriesPerPage = 20
# SearchGlobalID = ["EBAY-DE", "EBAY-IT", "EBAY-FR", "EBAY-AT",
#                   "EBAY-ES", "EBAY-IE", "EBAY-NL", "EBAY-NLBE", "EBAY-PL"]
SearchGlobalID = ["EBAY-DE", "EBAY-IT", "EBAY-PL"]
receiver_email = "receiver_email"  # enter your details
sender_email = "sender_email"  # enter your details
sender_email_pwd = "password"  # enter your details
smtp_server = "smtp.gmail.com"

# API prod key
AppID = "the-key-xyz-123"  # enter your details


# takes search parameters, makes POST for search and returns results response in JSON
def searchAndGetResponse(searchKeyword, searchMaxPrice, SearchEntriesPerPage, AppID, SearchGlobalID):
    url = "https://svcs.ebay.com/services/search/FindingService/v1"

    payload = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n" \
              "<findItemsAdvancedRequest xmlns=\"http://www.ebay.com/marketplace/search/v1/services\">\n" \
              "    <itemFilter>\n" \
              "        <name>listingType</name>\n" \
              "        <value>FixedPrice</value>\n" \
              "    </itemFilter>\n" \
              "    <itemFilter>\n" \
              "        <name>MaxPrice</name>\n" \
              "        <value>{0}</value>\n" \
              "        <paramName>Currency</paramName>\n" \
              "        <paramValue>EUR</paramValue>\n" \
              "    </itemFilter>\n" \
              "    <itemFilter>\n" \
              "        <name>HideDuplicateItems</name>\n" \
              "        <value>false</value>\n" \
              "    </itemFilter>\n" \
              "    <keywords>{1}</keywords>\n" \
              "    <sortOrder>StartTimeNewest</sortOrder>\n" \
              "    <categoryId>625</categoryId>\n" \
              "    <paginationInput>\n" \
              "        <entriesPerPage>{2}</entriesPerPage>\n" \
              "    </paginationInput>\n" \
              "</findItemsAdvancedRequest>".format(str(searchMaxPrice), searchKeyword, SearchEntriesPerPage)

    headers = {
        "X-EBAY-SOA-REQUEST-DATA-FORMAT": "xml",
        "X-EBAY-SOA-RESPONSE-DATA-FORMAT": "json",
        "X-EBAY-SOA-SECURITY-APPNAME": AppID,
        "X-EBAY-SOA-OPERATION-NAME": "findItemsAdvanced",
        "X-EBAY-SOA-GLOBAL-ID": SearchGlobalID,
        "Content-Type": "application/xml"
    }

    try:
        response1 = requests.request("POST", url, headers=headers, data=payload)
        response_j = json.loads(response1.text)
        print(SearchGlobalID + "\n" + str(response_j)[:200])
        return response_j
    except:
        response_err = ["errors"]
        return response_err


# takes JSON response and returns dict with extracted search results
def processResponse(restPy, nowTimeAdjusted):
    output1 = {}

    try:
        itemsFoundCount = int(restPy["findItemsAdvancedResponse"][0]["searchResult"][0]["@count"])
    # print("\n" + "Items found by search" + " - " + str(itemsFoundCount))
    except:
        output1 = False
        return output1

    # cycle through items:
    if itemsFoundCount > 0:
        itemsFound = restPy["findItemsAdvancedResponse"][0]["searchResult"][0]["item"]
        # print(str(itemsFound))
        for i in range(itemsFoundCount):
            # take item"s startTime and convert to date object ebayTimeFixed
            ebayTime = itemsFound[i]["listingInfo"][0]["startTime"][0]
            ebayTimeFixedStr = ebayTime.replace("Z", "000").replace("T", " ")
            ebayTimeFixed = datetime.strptime(ebayTimeFixedStr, "%Y-%m-%d %H:%M:%S.%f")

            # check if startTime is after adjusted current time nowTime
            if ebayTimeFixed > nowTimeAdjusted:
                output1.update({i: {"Title: ": itemsFound[i]["title"][0],
                                    "Kaina: ": itemsFound[i]["sellingStatus"][0]["currentPrice"][0],
                                    "Idetas: ": ebayTimeFixedStr.strip(".000000"),
                                    "URL: ": itemsFound[i]["viewItemURL"][0]}})
        if len(output1) > 0:
            return output1
        else:
            output1 = False
            return output1
    else:
        output1 = False
        return output1


# takes search results dict and formats into string ready to send via email
def formatMessage(outputas):

    emailMessage = ""
    # #print dictionary:
    for key in outputas:
        # print("---------------------------------------------------------------------")
        emailMessage = emailMessage + "---------------------------------------------------------------------\n"
        for x in outputas[key]:
            # print(x, outputas[key][x])
            emailMessage = emailMessage + x + str(outputas[key][x]) + "\n"
    return emailMessage


# takes formatted search results string and sends email
def sendEmail(receiver_email1, sender_email1, sender_email_pwd1, smtp_server1, message):
    port = 465  # For SSL


    # Create a secure SSL context
    context = ssl.create_default_context()

    with smtplib.SMTP_SSL(smtp_server1, port, context=context) as server:
        server.login(sender_email1, sender_email_pwd1)
        server.sendmail(sender_email1, receiver_email1, message)


while True:

    # get UTC timezone current time minus searchFreq minutes
    nowTimeAdjusted = datetime.utcnow() - timedelta(minutes=searchFreq)
    nowTime = datetime.utcnow()

    emailMessage = ""
    ifSendMail = 0
    # Cycle through all SearchGlobalID in the list, which represents regional EBAY portals.
    for SearchGlobalID_looped in SearchGlobalID:

        # make API call and check if no API/request error received. Try 4 times.
        for i in range(4):
            response = searchAndGetResponse(searchKeyword, searchMaxPrice, SearchEntriesPerPage, AppID,
                                            SearchGlobalID_looped)
            respCheck = list(response)[0]
            if respCheck == "errorMessage" or respCheck == "errors":
                print("API error, trying again\n")
                # mark output as False after 4th try
                if i == 3:
                    outputas = False
                continue
            else:
                print("API response received\n")
                outputas = processResponse(response, nowTimeAdjusted)
                break

        if outputas is not False:
            emailMessage = emailMessage + "\n\n" + "Results in " + SearchGlobalID_looped + " between " + nowTimeAdjusted.strftime(
                "%Y-%m-%d %H:%M:%S") + " GMT and " + nowTime.strftime(
                "%Y-%m-%d %H:%M:%S") + " GMT" + "\n" + formatMessage(outputas)
            # trigger email sending
            ifSendMail = ifSendMail + 1
        else:
            emailMessage = emailMessage + "\n" + SearchGlobalID_looped + " " + "Nieko naujo nerasta arba ivyko klaida\n"
        # print("Results in " + SearchGlobalID_looped + " between "+ nowTimeAdjusted.strftime("%Y-%m-%d %H:%M:%S") +" GMT and "+ nowTime.strftime("%Y-%m-%d %H:%M:%S") + " GMT")

    if ifSendMail > 0:
        try:
            sendEmail(receiver_email, sender_email, sender_email_pwd, smtp_server, emailMessage("utf-8"))
            print("\n~~~ email sent")
        except:
            print("\n~~~ email failed")
        print("\n~~~EMAIL MESSAGE~~~\n")
        print(emailMessage)

    else:
        print("\n~~~no need to send EMAIL MESSAGE~~~\n")
        print(emailMessage)

    print("Waiting " + str(searchFreq) + " minutes for next search")
    time.sleep(60 * searchFreq)
