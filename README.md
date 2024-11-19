# HTTP Response Chef
A simple python script for running a highly customizable HTTP server for testing very specific scenarios

## How to use
Just run the script using Python v3

`python3 ./HTTPResponseChef.py`

Use the `-h` flag for a list of arguments

To run in a simple docker container, just build from the Dockerfile and run with the following docker commands

`docker build -t http-response-chef:latest .`

`docker run -p 8888:8888 http-response-chef:latest`

The HTTP server will be hosted on port 8888 by default, so if you change the docker port mapping, you'll also need to provide the port argument to the python script

## How it works
The `HTTPResponseChef.py` script will start a very basic local HTTP server that, when handling a request, will map the request to a Recipe within the web server directory, process the Recipe, and return the resulting HTTP response. See `example` for a list of supported fields, and check out some of the other examples that I've added that illustrate how you can produce highly customized HTTP responses for testing.