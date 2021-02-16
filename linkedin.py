import http.cookiejar as cookielib
import os
import urllib
import re
import string
from bs4 import BeautifulSoup
import requests
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from datetime import date
from time import sleep
import pandas as pd
import re

username = "LINKEDINUSERNAMEHERE"
password = "LINKEDINPASSWORDHERE"

cookie_filename = "parser.cookies.txt"

LI_companies = {
    'MSFT' : '1035'
}

LI_countries = {
    'US' : 'United%20States'
}

useragent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.150 Safari/537.36'
delay = 100

class LinkedInParser(object):

    def __init__(self, login, password):
        """ Start up... """
        self.login = login
        self.password = password

        # Simulate browser with cookies enabled
        self.cj = cookielib.MozillaCookieJar(cookie_filename)
        if os.access(cookie_filename, os.F_OK):
            self.cj.load()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPRedirectHandler(),
            urllib.request.HTTPHandler(debuglevel=0),
            urllib.request.HTTPSHandler(debuglevel=0),
            urllib.request.HTTPCookieProcessor(self.cj)
        )
        self.opener.addheaders = [
            ('User-agent', 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:85.0) Gecko/20100101 Firefox/85.0')
        ]

        # Login
        self.loginPage()

        # title = self.loadTitle()
        # print(title)

        self.cj.save()

    def loadPage(self, url, data=None):
        """
        Utility function to load HTML from URLs for us with hack to continue despite 404
        """
        # We can print the url in case of infinite loop
        # print "Loading URL: %s" % url
        try:
            if data is not None:
                response = self.opener.open(url, data)
            else:
                response = self.opener.open(url)
            content = ''.join([str(l) for l in response.readlines()])
            # print("Page loaded: %s \n Content: %s \n" % (url, content))
            return content
        except Exception as e:
            # If URL doesn't load for ANY reason, try again...
            # Quick and dirty solution for 404 returns because of network problems
            # However, this could infinite loop if there's an actual problem
            print("Exception on %s load: %s" % (url, e))
            # return self.loadPage(url, data)


    def cleanup(self):
        os.remove("parser.cookies.txt")

    def loadSoup(self, url, data=None):
        """
        Combine loading of URL, HTML, and parsing with BeautifulSoup
        """
        html = self.loadPage(url, data)
        soup = BeautifulSoup(html, "html5lib")
        return soup

    def LI_Extract(self, companyID, country, data=None):
        companyID = LI_companies[companyID]
        country = LI_countries[country]
        url = f'https://www.linkedin.com/jobs/search/?f_C={companyID}&location={country}'
        options = Options()
        browser = webdriver.Firefox(options=options)
        browser.get(url)
        for cookie in self.cj:
            cookie_dict = {'domain': cookie.domain, 'name': cookie.name, 'value': cookie.value, 'secure': cookie.secure}
            if cookie.expires:
                cookie_dict['expiry'] = cookie.expires
            if cookie.path_specified:
                cookie_dict['path'] = cookie.path
            browser.add_cookie(cookie_dict)
            print(cookie_dict)
        browser.get(url)
        try:
            WebDriverWait(browser, delay).until(
            EC.presence_of_element_located((By.ID, "ember32")))
        # change the "ember32" for the id of the image you have as your linked in picture, this only loads when you are logged in
        except TimeoutException:
            print('Loading took too much time!')
        else:
            html = browser.page_source
            browser.quit()
        if html:
            # display to check: 
            soup = BeautifulSoup(html, 'html.parser')
            return soup
        else:
            print('Could not locate job listing results number!')
        

    def loginPage(self):
        """
        Handle login. This should populate our cookie jar.
        """
        soup = self.loadSoup("https://www.linkedin.com/login")
        try:
            loginCsrfParam = soup.find("input", {"name": "loginCsrfParam"})['value']
            csrfToken = soup.find("input", {"name": "csrfToken"})['value']
            sIdString = soup.find("input", {"name": "sIdString"})['value']
            print("loginCsrfParam: %s" % loginCsrfParam)
            print("csrfToken: %s" % csrfToken)
            print("sIdString: %s" % sIdString)
            login_data = urllib.parse.urlencode({
                'session_key': self.login,
                'session_password': self.password,
                'loginCsrfParam': loginCsrfParam,
                'csrfToken': csrfToken,
                'sIdString': sIdString
            }).encode('utf8')

            self.loadPage("https://www.linkedin.com/checkpoint/lg/login-submit", login_data)
        
        except TypeError:
            print("It went wrong, login and cookie details not found")
            self.cleanup()

    def loadTitle(self):
        soup = self.loadSoup("https://www.linkedin.com/feed/")
        
    def LI_Transform_and_save(soup,company,country,save=True):
        listings = str(soup.find('small', class_ = 'display-flex').text)
        listings_numbers = re.findall('[0-9]+', listings)
        listings = ''.join(map(str, listings_numbers))
        filename = 'LINKEDIN-%s-data.csv' % (company)
        datapath = 'data'
        filename = os.path.join(".." + os.sep, datapath + os.sep, filename)
        if os.path.isfile(filename): data_df = pd.read_csv(filename)
        else: data_df = pd.DataFrame()
        data = pd.DataFrame({'date':[date.today()],'company':[company],'country':[country],'listings':[listings]})
        if len(data_df) > 0:
            data_df = pd.concat([data_df, data],join="outer",ignore_index=True)
            data_df.drop_duplicates(subset=['date','company','country'])
        else: data_df = data
        data_df.set_index('date', inplace=True)
        if save: data_df.to_csv(filename)
        print('All caught up on ' + company + " in " + country + "!" )

companies = ['MSFT']

countries = ['US']

user = LinkedInParser(username, password)

for company in companies:
    for country in countries:
        soup = LinkedInParser.LI_Extract(user,company,country)
        LinkedInParser.LI_Transform_and_save(soup,company,country)
        sleep(5)

LinkedInParser.cleanup(user)
