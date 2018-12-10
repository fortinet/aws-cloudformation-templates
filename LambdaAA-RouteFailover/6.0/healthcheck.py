import os
import sys
import socket
import boto3
import logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)
ec2client = boto3.client('ec2')

try:
    az1ip,az2ip = os.environ['InstanceIPs'].split(',')
    az1eni,az2eni = os.environ['InstanceENIs'].split(',')
    az1rts = os.environ['az1RouteTables'].split(',')
    az2rts = os.environ['az2RouteTables'].split(',')
except Exception as ERROR:
    print('<--!! Exception in environment variables: {}'.format(ERROR))
    sys.exit()

if os.environ['HealthCheckPort'].split():
    hcport = os.environ['HealthCheckPort']
else:
    logging.error('<--!! HealthCheckPort is Empty')
    sys.exit()

class get_hc_status(object):
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.status = None
        logger.debug('--> Checking Host+Port {}:{}'.format(self.ip, self.port))
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5)
        try:
            s.connect((self.ip, int(self.port)))
            s.shutdown(2)
            self.status = True
            logger.info('<-- Host+Port {}:{} is UP = {}'.format(self.ip, self.port, self.status))
        except Exception as ERROR:
            s.close()
            self.status = False
            logger.error('<--!! Exception in get_hc_status: {}'.format(ERROR))
            logger.info('<-- Host+Port {}:{} is UP = {}'.format(self.ip, self.port, self.status))

class get_routes(object):
    def __init__(self, routetables, eni1, eni2):
        self.rts = routetables
        self.eni1 = eni1
        self.eni2 = eni2
        self.count = 0
        self.hit = None
        self.routemap = {}
        for rt in self.rts:
            logger.debug('--> Getting routes in rt {} which target {} or {}'.format(rt, self.eni1, self.eni2))
            try:
                response = ec2client.describe_route_tables(RouteTableIds=[rt])
                logger.debug('<-- Response: {}'.format(response))
            except Exception as ERROR:
                logger.error('<--!! Exception in get_routes: {}'.format(ERROR))
                sys.exit()
            for route in response['RouteTables'][0]['Routes']:
                if 'NetworkInterfaceId' in route:
                    if self.eni1 in route['NetworkInterfaceId'] or self.eni2 in route['NetworkInterfaceId']:
                        self.count += 1
                        self.routemap[self.count] = [rt, route['DestinationCidrBlock'], route['NetworkInterfaceId']]
                        self.hit = True
                        logger.debug('<-- Matching Route Found: {}'.format(route))
        if self.hit is None:
            self.hit = False
            logger.debug('<-- NO Matching Routes Found!')

def check_routes(routemap, az, eni):
    logger.debug('--> Checking routes in az {} point to {}'.format(az, eni))
    try:
        for key,value in routemap.iteritems():
            rmrt,rmroute,rmeni = value
            if eni in rmeni:
                logger.debug('<-- Matching Route Found: rt {} route {} point to {}'.format(rmrt, rmroute, rmeni))
                pass
            else:
                logger.debug('<-- NO Matching Route Found!')
                return False
        return True
    except Exception as ERROR:
        logger.error('<--!! Exception in check_routes: {}'.format(ERROR))

def replace_routes(routemap, az, eni):
    logger.debug('--> Updating routes in az {} to target {}'.format(az, eni))
    try:
        for key,value in routemap.iteritems():
            rmrt,rmroute,rmeni = value
            response = ec2client.replace_route(NetworkInterfaceId=eni,RouteTableId=rmrt,DestinationCidrBlock=rmroute)
            if response['ResponseMetadata']['HTTPStatusCode'] == int(200):
                logger.info('--> Updated {} in rt {} to target {}'.format(rmroute, rmrt, eni))
    except Exception as ERROR:
        logger.error('<--!! Exception in replace_routes: {}'.format(ERROR))

def lambda_handler(event, context):
    logger.info('-=-' * 20)
    logger.debug('>> az1ip: {}'.format(az1ip))
    logger.debug('>> az2ip: {}'.format(az2ip))
    logger.debug('>> az1eni: {}'.format(az1eni))
    logger.debug('>> az2eni: {}'.format(az2eni))
    logger.debug('>> az1rts: {}'.format(az1rts))
    logger.debug('>> az2rts: {}'.format(az2rts))
    logger.debug('>> hcport: {}'.format(hcport))
    az1hc = get_hc_status(az1ip, hcport)
    az1routes = get_routes(az1rts, az1eni, az2eni)
    az2hc = get_hc_status(az2ip, hcport)
    az2routes = get_routes(az2rts, az1eni, az2eni)
    if az1hc.status and az2hc.status is True:
        if az1routes.hit is True and check_routes(az1routes.routemap, '1', az1eni) is False:
            replace_routes(az1routes.routemap, '1', az1eni)
        if az2routes.hit is True and check_routes(az2routes.routemap, '2', az2eni) is False:
            replace_routes(az2routes.routemap, '2', az2eni)
    elif az1hc.status is True and az2hc.status is False:
        if az1routes.hit is True and check_routes(az1routes.routemap, '1', az1eni) is False:
            replace_routes(az1routes.routemap, '1', az1eni)
        if az2routes.hit is True and check_routes(az2routes.routemap, '2', az1eni) is False:
            replace_routes(az2routes.routemap, '2', az1eni)
    elif az1hc.status is False and az2hc.status is True:
        if az1routes.hit is True and check_routes(az1routes.routemap, '1', az2eni) is False:
            replace_routes(az1routes.routemap, '1', az2eni)
        if az2routes.hit is True and check_routes(az2routes.routemap, '2', az2eni) is False:
            replace_routes(az2routes.routemap, '2', az2eni)
    logger.info('-=-' * 20)
#
# end of script
#