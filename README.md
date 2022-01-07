# HI-Public-Notices
 Scrapes the https://statelegals.staradvertiser.com/category/public-notices/ website and adds notices to a sql database

## TODO
Better date range options
Don't allow duplicates in the database.
Error catching on insert into sql if failed. This is needed because it's on a relatively small sql db.

## Setup
```
git@github.com:Coding4Lawyers/HI-Poublic_Notices.git
cd HI-Poublic_Notices
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
```
## Use
```
python main.py
```
If the first argument is "All" it will scrape all the notices. This is useful for starting off.
```
python main.py All 
```

## Cronjob
```
0 12 * * * /home/ubuntu/HI-Poublic_Notices/venv/bin/python /home/ubuntu/HI-Poublic_Notices/main.py >> /home/ubuntu/HI-Poublic_Notices/cronlog.log 2>&1
```

