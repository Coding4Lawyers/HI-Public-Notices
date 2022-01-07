import requests
from bs4 import BeautifulSoup
import time
import csv
import mysql.connector
from datetime import datetime
import pytz
import passwords
import sys

#I had to run "ALTER TABLE HIProjects.public_notices CONVERT TO CHARACTER SET utf8" on the sql table to get it to encode right.
#0 6 * * * $(which python3) /home/ubuntu/publicnotices.py >> ~/cron.log 2>&1

#TODO: Better date range options
#TODO: Don't allow duplicates in the database.
#TODO: Error catching on insert into sql if failed. This is needed because it's on a relatively small sql db.


def insertSQL(notice):
    #Insert the new record into the sql table.
    #This function only inserts one at a time.
    mydb = mysql.connector.connect(
        host=passwords.host,
        user=passwords.user,
        password=passwords.password,
        database=passwords.database
    )

    mycursor = mydb.cursor()
    timestamp = datetime.now(pytz.timezone('Pacific/Honolulu'))
    sql = "INSERT INTO public_notices (Notice_Type,Publication_Date,Newspaper,Full_Description_Link,Brief_Description,Full_Description,Timestamp) " \
          "VALUES (%s, %s,%s, %s,%s, %s,%s)"
    val = (notice['Notice Type'],notice['Publication Date'],notice['Newspaper'],notice['Link'], notice['Brief Description'],notice['Full Description'],timestamp)
    mycursor.execute(sql, val)

    mydb.commit()

    print(mycursor.rowcount, "record inserted.")

def scrapeFullDescription(url):
    #Go do the full description page and grab that.
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36'}
    r = requests.get(url,headers = headers)
    #print(r.text)
    html = r.text
    soup = BeautifulSoup(html,'lxml')
    description = soup.find('div',attrs={'class':'entry-content'}).text.strip()
    return description
def scrapeNoticesFromPage(url,collectall):
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
            if(collectall == False and correcteddate.date() != datetime.now(pytz.timezone('Pacific/Honolulu')).date()):
                #Means this is not an anouncement from today
                #This could be a problem if they post notices and back date them.
                #The collectall variable is set by the user
                continue

            notice['Publication Date'] = correcteddate
            contentrow = row.find('td',attrs={'class':'tdlisting'})
            newspaperspan = contentrow.find_all('span')[0]
            newspaper = newspaperspan.text
            #print("Newspaper", newspaper)
            notice['Newspaper'] = newspaper[13:]
            full_desciption_atag = contentrow.find_all('a')[1]
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
            print("Found new public notice",notice['Notice Type'],date,notice['Link'])
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


if __name__ == "__main__":
    print("Starting Scrape",datetime.now(pytz.timezone('Pacific/Honolulu')))
    #This is a an argument that allows the program to capture all the eventsd. This is good for starting over and populating a full db/csv
    #The default is collecting just today.
    if(len(sys.argv) > 0 and sys.argv[1] == "All"):
        collectall = True
    else:
        collectall = False
    notices = []
    url = 'https://statelegals.staradvertiser.com/category/public-notices/' #This will automatically start with page 1

    #Keep looping until the return from the scrapeNoticesFromPage() function is none, meaning we have no more pages.
    while url != None:
        #Each loop represent a page of notices.
        print("Scraping",url)
        results = scrapeNoticesFromPage(url,collectall)
        notices.extend(results[0])
        url = results[1]
        time.sleep(1)

    #Saving to SQL DB
    # Send the new notice record to the insertSQL function to save it to the SQL DB.
    if len(notices) > 0:
        for notice in notices:
            insertSQL(notice)
        #createCSV(notices) #Uncomment below to save all the notices to csv.
    print("Ending scrape")
    print("\n\n")



