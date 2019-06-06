FROM python:3.6

ENV http_proxy="http://wwwproxy.unimelb.edu.au:8000"
ENV https_proxy="http://wwwproxy.unimelb.edu.au:8000"
ENV ftp_proxy="http://wwwproxy.unimelb.edu.au:8000"

ADD processedTwitterRetriver.py /

RUN pip install CouchDB

CMD [ "python3", "./processedTwitterRetriver.py" ]