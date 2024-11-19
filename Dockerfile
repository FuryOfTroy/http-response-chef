FROM python:3

ADD ./* /

CMD [ "python", "./HTTPResponseChef.py" ]