# Arxiv-filter
The goal of the arxiv-filter is to output the recent releases in Arxiv, filtered by keywords.
The output is an HTML page with the relevant abstracts, and links to the PDFs.
Change the "setting.ini" file as necessary, you can:
1) Filter by kewords in the PDF of the paper

2) Filter by keywords in the abstract to accelrate the process 

3) Change the amount of recent papers to extract, note that it is not possible to filter by dates only by recent uploads

4) Check only new uploads or also updates to existing papers

5) and a couple of more options...


In order for it to run the following Python libraries are required: urllib, feedparser, PyPDF2, dominate
