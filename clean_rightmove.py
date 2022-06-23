import time
from argparse import ArgumentParser

from selenium.webdriver import Chrome, ChromeOptions
from selenium.webdriver.support.expected_conditions import visibility_of_element_located
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from bs4 import BeautifulSoup


class RightmoveCleaner(Chrome):
    def __init__(self, executable_path, *args, **kwargs):
        op = ChromeOptions()
        op.add_argument("window-size=1400,600")
        # op.add_argument("--headless")
        op.add_experimental_option("excludeSwitches", ["enable-logging"])

        super().__init__(executable_path=executable_path, options=op, *args, **kwargs)

        self.unavailable_listings = []

    def login_rightmove(self, email, password):

        self.get("https://www.rightmove.co.uk/login.html")
        email_elem = self.find_element_by_css_selector("input#email")
        email_elem.send_keys(email)

        password_elem = self.find_element_by_css_selector("input#password")
        password_elem.send_keys(password)

        self.find_element_by_css_selector("button#my-submit-button").click()
        time.sleep(4)

    def get_unavailable_listings(self):
        self.get(f"https://www.rightmove.co.uk/user/shortlist.html")

        pagination = WebDriverWait(self, 20).until(
            visibility_of_element_located((By.CSS_SELECTOR, "select#pagination"))
        )
        no_pages = int(pagination.text.split("\n")[-1])

        for page_number in range(1, no_pages + 1):
            self.get(
                f"https://www.rightmove.co.uk/user/shortlist.html?channel=RES_LET&page={page_number}&sortBy=DATE_ADDED&orderBy=DESC"
            )
            listings_elem = WebDriverWait(self, 20).until(
                visibility_of_element_located((By.CLASS_NAME, "body-container"))
            )
            listings_soup = BeautifulSoup(
                self.execute_script("return arguments[0].innerHTML;", listings_elem)
            )

            for listing in listings_soup.find_all("li"):
                status = listing.find_all(class_="status")
                status = status[0].text.strip("\n").strip() if status else ""

                if status == "Let agreed":
                    self.unavailable_listings.append(self.get_listing_link(listing))
                    continue

                unpublished_message = listing.find_all(
                    "p", class_="unpublished-message"
                )
                if (
                    unpublished_message
                    and unpublished_message[0].text.strip("\n").strip()
                    == "No longer on the market"
                ):
                    self.unavailable_listings.append(self.get_listing_link(listing))

        self.unavailable_listings = [
            f"https://www.rightmove.co.uk{listing}"
            for listing in self.unavailable_listings
        ]

    @staticmethod
    def get_listing_link(listing):
        return listing.find_all("a", attrs={"data-test": "saved-property-title"})[0][
            "href"
        ]

    def unsave_unavailable_listings(self):
        for listing in self.unavailable_listings:
            self.get(listing)

            try:
                self.find_element_by_class_name("propertyUnpublished")
                with open("to_remove_manually.txt", "a") as f:
                    f.write(f"{listing}\n")
                continue
            except NoSuchElementException:
                pass

            unsave_button = self.find_element(
                By.CSS_SELECTOR,
                'button[title="Unsave this property"][data-test="saveHeart"]',
            )
            self.execute_script("arguments[0].click()", unsave_button)

    def clean_unavailable_listings(self):
        self.get_unavailable_listings()
        self.unsave_unavailable_listings()


if __name__ == "__main__":
    ap = ArgumentParser()
    ap.add_argument("--email", "-e", required=True)
    ap.add_argument("--password", "-p", required=True)
    credentials = vars(ap.parse_args())
    DRIVER_LOCATION = "./chromedriver.exe"
    rightmove_cleaner = RightmoveCleaner(DRIVER_LOCATION)
    rightmove_cleaner.login_rightmove(**credentials)
    rightmove_cleaner.clean_unavailable_listings()
    quit()
