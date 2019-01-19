FROM alpine:3.4

RUN echo "http://dl-cdn.alpinelinux.org/alpine/latest-stable/main" > /etc/apk/repositories
RUN echo "http://dl-cdn.alpinelinux.org/alpine/latest-stable/community" >> /etc/apk/repositories
RUN apk --no-cache --update-cache add gcc gfortran openblas-dev python3-dev build-base freetype-dev
RUN ln -s /usr/include/locale.h /usr/include/xlocale.h
RUN pip3 install --upgrade pip
RUN pip3 install numpy scipy pandas

COPY requirements.txt /app/
WORKDIR /app/
    
# RUN python -m venv venv
RUN pip3 install -r requirements.txt

COPY app.py .
COPY processing.py .

# py-pip build-base wget freetype-dev libpng-dev 