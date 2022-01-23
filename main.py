import requests
from bs4 import BeautifulSoup
import time
import csv
import mysql.connector
from datetime import datetime
import pytz
import passwords



def checkIfAlreadyExistsInDB(notice,table_name):
    mydb = mysql.connector.connect(
        host=passwords.host,
        user=passwords.user,
        password=passwords.password,
        database=passwords.database
    )
    mycursor = mydb.cursor()
    sql = "SELECT * FROM " + table_name + " WHERE Notice_Type = %s and Publication_Date = %s and Full_Description_Link = %s and Newspaper = %s and Full_Description = %s"
    val = (notice['Notice Type'],notice['Publication Date'],notice['Link'],notice['Newspaper'],notice['Full Description'],)

    mycursor.execute(sql, val)
    records = mycursor.fetchall()
    return len(records)
def insertSQL(notice,table_name):
    #Insert the new record into the sql table.
    #This function only inserts one at a time.

    if(checkIfAlreadyExistsInDB(notice,table_name) > 0):
        #print(notice['Link'],"is already in the db")
        return False

    mydb = mysql.connector.connect(
        host=passwords.host,
        user=passwords.user,
        password=passwords.password,
        database=passwords.database
    )

    mycursor = mydb.cursor()
    timestamp = datetime.now(pytz.timezone('Pacific/Honolulu'))
    sql = "INSERT INTO " + table_name + " (Notice_Type,Publication_Date,Newspaper,Full_Description_Link,Brief_Description,Full_Description,Timestamp) " \
          "VALUES (%s, %s,%s, %s,%s, %s,%s)"
    val = (notice['Notice Type'],notice['Publication Date'],notice['Newspaper'],notice['Link'], notice['Brief Description'],notice['Full Description'],timestamp)
    mycursor.execute(sql, val)

    mydb.commit()

    print(notice['Publication Date'], notice['Link'], "record inserted.")
    return True

def scrapeFullDescription(url):
    #Go do the full description page and grab that.
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36'}
    r = requests.get(url,headers = headers)
    #print(r.text)
    html = r.text
    soup = BeautifulSoup(html,'lxml')
    description = soup.find('div',attrs={'class':'entry-content'}).text.strip()
    return description
def scrapeNoticesFromPage(url):
    #Go to the summary page and cycle through and get all the urls.
    #This should be called once for each possible page
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36'}
    r = requests.get(url,headers = headers)
    html = r.text
    notices = []
    soup = BeautifulSoup(html,'lxml')
    h4s = soup.find_all('h4') #Has the titles
    for h4 in h4s:
        notice_type = h4.text
        table = h4.find_next_sibling('table',attrs={'class':'listtable'})
        rows = table.find_all('tr')
        for row in rows:
            notice = {}
            notice['Notice Type'] = notice_type
            date = row.find('td',attrs={'class':'tddate'}).text
            #print("Date:",date)
            year = datetime.now(pytz.timezone('Pacific/Honolulu')).year
            correcteddate = datetime.strptime(date + " " + str(year),'%b %d %Y')
            correcteddate = correcteddate.replace(tzinfo=pytz.timezone('Pacific/Honolulu'))
            if(correcteddate > datetime.now(pytz.timezone('Pacific/Honolulu'))):
                #This means this is actually from the last year.
                #Delete one from the year so we put it in the right year
                correcteddate = datetime.strptime(date + " " + str(year-1), '%b %d %Y')

            notice['Publication Date'] = correcteddate
            contentrow = row.find('td',attrs={'class':'tdlisting'})
            if(url[0:38] == "https://statelegals.staradvertiser.com"):
                newspaperspan = contentrow.find_all('span')[0]
                newspaper = newspaperspan.text
                #print("Newspaper", newspaper)
                notice['Newspaper'] = newspaper[13:]
                full_desciption_atag = contentrow.find_all('a')[1]
            else:
                #This is for Hawaii Classifieds which has a slightly different structure and no newspaper
                notice['Newspaper'] = None
                full_desciption_atag = contentrow.find('a')

            full_description_link = full_desciption_atag['href']
            #print("Link",full_description_link)
            notice['Link'] = full_description_link
            briefdescription = full_desciption_atag.text.strip()
            #print("Brief Description",briefdescription)
            notice['Brief Description'] = briefdescription.encode('utf-8')
            time.sleep(1) #Add in a time delay so we don't scrape too fast

            #Call the scrape full description function using the new link
            full_description = scrapeFullDescription(full_description_link)
            notice['Full Description'] = full_description.encode('utf-8')
            #print("Found notice",notice['Notice Type'],date,notice['Link'])
            notices.append(notice)


    #Check to see if the link for the Next page appears. If it does then we have more pages. If not then we can stop.
    nexturltag = soup.find('a', text='Next »')
    nexturl = None
    if(nexturltag != None):
        nexturl = nexturltag['href']
    return (notices,nexturl)

def createCSV(notices):
    #Create a CSV with all the returned notices
    with open('Notices.csv', 'w', newline='',encoding="utf-8") as csvfile:
        fieldnames = notices[0].keys()
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(notices)

def loopThroughPages(url):
    #This needs to be done up here because eventually the url is equal to none at the end of the pages.
    if (url[0:38] == "https://statelegals.staradvertiser.com"):
        table_name = "star_advertiser"
    else:
        table_name = "hawaii_classifieds"

    #Keep looping until the return from the scrapeNoticesFromPage() function is none, meaning we have no more pages.
    while url != None:
        #Each loop represent a page of notices.
        print("Scraping",url)
        results = scrapeNoticesFromPage(url)
        notices.extend(results[0])
        url = results[1]
        time.sleep(1)

    #Saving to SQL DB
    # Send the new notice record to the insertSQL function to save it to the SQL DB.

    records_inserted = 0
    if len(notices) > 0:
        for notice in notices:
            try:
                if(insertSQL(notice,table_name) == True):
                    records_inserted += 1
            except Exception as e:
                print("Error in SQL Insertion")
                print(e)
        #createCSV(notices) #Uncomment below to save all the notices to csv.
    print("New Records Inserted",records_inserted)
if __name__ == "__main__":
    print("Starting Scrape",datetime.now(pytz.timezone('Pacific/Honolulu')))
    notices = []
    print("Scraping Star Advertiser")
    url = 'https://statelegals.staradvertiser.com/category/public-notices/' #This will automatically start with page 1
    loopThroughPages(url)

    print("Scraping Hawaii Classifieds")
    # url = 'https://hawaiisclassifieds.com/category/legal-notices/'  # This will automatically start with page 1
    # loopThroughPages(url)
    print("Ending scrape")
    print("\n\n")



