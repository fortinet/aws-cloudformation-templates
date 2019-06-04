import os
import sys
import socket
import datetime
import logging
import boto3
logger = logging.getLogger()
logger.setLevel(logging.INFO)
ec2client = boto3.client('ec2', endpoint_url=os.environ['VPCEndpointURL'])

class get_instanceinfo(object):
    def __init__(self, vpcid, hapairvalue):
        self.active_id = ''
        self.active_eni0_id = ''
        self.active_eni0_ip = ''
        self.active_eni0_ip_map = {}
        self.active_eni0_route_map = {}
        self.active_eni1_id = ''
        self.active_eni1_ip = ''
        self.active_eni1_route_map = {}
        self.passive_id = ''
        self.passive_eni0_id = ''
        self.passive_eni0_ip = ''
        self.passive_eni0_ip_map = {}
        self.passive_eni0_route_map = {}
        self.passive_eni1_id = ''
        self.passive_eni1_ip = ''
        self.passive_eni1_route_map = {}
        try:
            ec2search = ec2client.describe_instances(Filters=[{'Name':'vpc-id', 'Values':[vpcid]}, {'Name':'tag:ha:pair', 'Values':[hapairvalue]}])
            if ec2search['ResponseMetadata']['HTTPStatusCode'] != int(200):
                logger.error('<--!! Error seen when searching for instances in vpc {} with matching ha:pair tag value {}: {}'.format(vpcid, hapairvalue, ec2search))
        except Exception as error:
            logger.error('<--!! Exception in describe_instances step in get_instanceinfo: {}'.format(error))
            sys.exit()
        instance_ids = []
        for result in ec2search['Reservations']:
            for hit in result['Instances']:
                if 'InstanceId' in hit:
                    instance_ids.append(hit['InstanceId'])
        if len(instance_ids) != 2:
            logger.error('<--!! The number of instances found in vpc {} with matching ha:pair tag value {} does not equal 2! {}'.format(vpcid, hapairvalue, instance_ids))
            sys.exit()
        else:
            logger.info('--> Found matching instances: {}'.format(instance_ids))
        for instances in ec2search['Reservations']:
            for instance in instances['Instances']:
                count1, count2, count3 = 0, 0, 0
                for tag in instance['Tags']:
                    if 'ha:status' in tag['Key'] and 'active' in tag['Value']:
                        self.active_id = instance['InstanceId']
                        for eni in instance['NetworkInterfaces']:
                            if eni['Attachment']['DeviceIndex'] == 0:
                                self.active_eni0_id = eni['NetworkInterfaceId']
                                self.active_eni0_ip = eni['PrivateIpAddress']
                                for addr in eni['PrivateIpAddresses']:
                                    if addr['Primary'] is False:
                                        count1 += 1
                                        self.active_eni0_ip_map[count1] = [eni['NetworkInterfaceId'], addr['PrivateIpAddress']]
                            if eni['Attachment']['DeviceIndex'] == 1:
                                self.active_eni1_id = eni['NetworkInterfaceId']
                                self.active_eni1_ip = eni['PrivateIpAddress']
                        rts = ec2client.describe_route_tables(Filters=[{'Name':'vpc-id', 'Values':[vpcid]}, {'Name':'route.instance-id', 'Values':[self.active_id]}])
                        for rt in rts['RouteTables']:
                            for route in rt['Routes']:
                                if 'InstanceId' in route:
                                    if self.active_id in route['InstanceId'] and self.active_eni0_id in route['NetworkInterfaceId']:
                                        count2 += 1
                                        self.active_eni0_route_map[count2] = [rt['RouteTableId'], route['DestinationCidrBlock'], route['NetworkInterfaceId']]
                                    if self.active_id in route['InstanceId'] and self.active_eni1_id in route['NetworkInterfaceId']:
                                        count3 += 1
                                        self.active_eni1_route_map[count3] = [rt['RouteTableId'], route['DestinationCidrBlock'], route['NetworkInterfaceId']]
                    if 'ha:status' in tag['Key'] and 'passive' in tag['Value']:
                        self.passive_id = instance['InstanceId']
                        for eni in instance['NetworkInterfaces']:
                            if eni['Attachment']['DeviceIndex'] == 0:
                                self.passive_eni0_id = eni['NetworkInterfaceId']
                                self.passive_eni0_ip = eni['PrivateIpAddress']
                                for addr in eni['PrivateIpAddresses']:
                                    if addr['Primary'] is False:
                                        count1 += 1
                                        self.passive_eni0_ip_map[count1] = [eni['NetworkInterfaceId'], addr['PrivateIpAddress']]
                            if eni['Attachment']['DeviceIndex'] == 1:
                                self.passive_eni1_id = eni['NetworkInterfaceId']
                                self.passive_eni1_ip = eni['PrivateIpAddress']
                        rts = ec2client.describe_route_tables(Filters=[{'Name':'vpc-id', 'Values':[vpcid]}, {'Name':'route.instance-id', 'Values':[self.passive_id]}])
                        for rt in rts['RouteTables']:
                            for route in rt['Routes']:
                                if 'InstanceId' in route:
                                    if self.passive_id in route['InstanceId'] and self.passive_eni0_id in route['NetworkInterfaceId']:
                                        count2 += 1
                                        self.passive_eni0_route_map[count2] = [rt['RouteTableId'], route['DestinationCidrBlock'], route['NetworkInterfaceId']]
                                    if self.passive_id in route['InstanceId'] and self.passive_eni1_id in route['NetworkInterfaceId']:
                                        count3 += 1
                                        self.passive_eni1_route_map[count3] = [rt['RouteTableId'], route['DestinationCidrBlock'], route['NetworkInterfaceId']]

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
        except Exception as error:
            s.close()
            self.status = False
            logger.error('<--!! Exception in get_hc_status: {}'.format(error))
            logger.info('<-- Host+Port {}:{} is UP = {}'.format(self.ip, self.port, self.status))

def reassign_eips(activemap, passivemap):
    logger.debug('--> Updating EIPs to target new active instance')
    if len(activemap) != len(passivemap):
        logger.error('<--!! Instances ENI0 secondaryIP count does not match!')
        logger.error('<--!! This will likely affect EIP reassignment!')
    try:
        for key in activemap:
            avalue = activemap[key]
            pvalue = passivemap[key]
            logger.debug('--> Found matching ENI0 secondaryIPs {} to {}'.format(avalue, pvalue))
            aeni, aip = avalue
            peni, pip = pvalue
            try:
                aeip = ec2client.describe_addresses(Filters=[{'Name':'network-interface-id', 'Values':[aeni]}, {'Name':'private-ip-address', 'Values':[aip]}])
            except Exception as error:
                logger.error('<--!! Exception in describe_addresses step in reassign_eips: {}'.format(error))
            if aeip['ResponseMetadata']['HTTPStatusCode'] == int(200):
                if aeip['Addresses']:
                    try:
                        response = ec2client.associate_address(AllowReassociation=True, AllocationId=aeip['Addresses'][0]['AllocationId'], NetworkInterfaceId=peni, PrivateIpAddress=pip)
                        if response['ResponseMetadata']['HTTPStatusCode'] == int(200):
                            logger.info('--> Updated {} to target {} {}'.format(aeip['Addresses'][0]['PublicIp'], peni, pip))
                        else:
                            logger.error('<--!! Error seen when updating {} to target {} {}: {}'.format(aeip['Addresses'][0]['PublicIp'], peni, pip, response))
                    except Exception as error:
                        logger.error('<--!! Exception in associate_address step in reassign_eips: {}'.format(error))
            else:
                logger.error('<--!! Error seen when updating {} to target {} {}: {}'.format(aeip['Addresses'][0]['PublicIp'], peni, pip, aeip))
    except Exception as error:
        logger.error('<--!! Exception in reassign_eips: {}'.format(error))

def replace_routes(map, eni):
    logger.debug('--> Updating routes to target {}'.format(eni))
    try:
        for key, value in map.iteritems():
            mrt, mroute, meni = value
            if eni:
                response = ec2client.replace_route(NetworkInterfaceId=eni, RouteTableId=mrt, DestinationCidrBlock=mroute)
                if response['ResponseMetadata']['HTTPStatusCode'] == int(200):
                    logger.info('--> Updated {} in rt {} to target {}'.format(mroute, mrt, eni))
                else:
                    logger.error('<--!! Error seen when updating {} in rt {} to target {}: {}'.format(mroute, mrt, eni, response))
    except Exception as error:
        logger.error('<--!! Exception in replace_routes: {}'.format(error))

def update_tags(activeid, passiveid):
    try:
        if activeid:
            ec2client.create_tags(Resources=[activeid], Tags=[{'Key': 'ha:status', 'Value': 'active'}])
            ec2client.create_tags(Resources=[activeid], Tags=[{'Key': 'ha:time', 'Value': str(datetime.datetime.now())}])
            logger.info('--> Updated tags for active instance: {}'.format(activeid))
        if passiveid:
            ec2client.create_tags(Resources=[passiveid], Tags=[{'Key': 'ha:status', 'Value': 'passive'}])
            ec2client.create_tags(Resources=[passiveid], Tags=[{'Key': 'ha:time', 'Value': str(datetime.datetime.now())}])
            logger.info('--> Updated tags for passive instance: {}'.format(passiveid))
    except Exception as error:
        logger.error('<--!! Exception in update_tags: {}'.format(error))

def lambda_handler(event, context):
    logger.info('-=-' * 20)
    if 'source' in event:
        if 'aws.events' in event['source']:
            logger.info('>> Triggered by CloudWatch Scheduled Event <<')
    if 'data' in event:
        if 'stitch' in event['data']:
            logger.info('>> Triggered by FortiOS Stitch Action <<')
    if os.environ['VPCID'] and os.environ['HAPairValue'] and os.environ['HealthCheckPort'].isdigit():
        ha = get_instanceinfo(os.environ['VPCID'], os.environ['HAPairValue'])
    else:
        logger.error('<--!! Exception in environment variables: VPCID should be a single VPC ID value')
        logger.error('<--!! Exception in environment variables: HAPairValue should be a single string value following AWS tag value restrictions')
        logger.error('<--!! Exception in environment variables: HealthCheckPort should be a single tcp port number')
        sys.exit()
    if ha.active_eni1_ip and ha.passive_eni1_ip:
        hcactive = get_hc_status(ha.active_eni1_ip, os.environ['HealthCheckPort'])
        hcpassive = get_hc_status(ha.passive_eni1_ip, os.environ['HealthCheckPort'])
    else:
        hcactive = get_hc_status(ha.active_eni0_ip, os.environ['HealthCheckPort'])
        hcpassive = get_hc_status(ha.passive_eni0_ip, os.environ['HealthCheckPort'])
    if hcactive.status is True:
        if hcpassive.status is True:
            logger.info('-->> Active is up, Passive is up: Checking routes point to Active')
        if hcpassive.status is False:
            logger.info('-->> Active is up, Passive is down: Checking routes point to Active')
        if ha.passive_eni0_route_map:
            logger.error('!!-->> Found routes pointing to Passive ENI0: Moving routes to Active')
            replace_routes(ha.passive_eni0_route_map, ha.active_eni0_id)
            update_tags(ha.active_id, ha.passive_id)
        if ha.passive_eni1_route_map:
            logger.error('!!-->> Found routes pointing to Passive ENI1: Moving routes to Active')
            replace_routes(ha.passive_eni1_route_map, ha.active_eni1_id)
            update_tags(ha.active_id, ha.passive_id)
    elif hcactive.status is False and hcpassive.status is True:
        logger.error('-->> Active is down but Passive is up: Moving EIPs & routes to Passive')
        logger.error('-->> Triggering_CloudWatch_Failover_Alarm')
        reassign_eips(ha.active_eni0_ip_map, ha.passive_eni0_ip_map)
        replace_routes(ha.active_eni0_route_map, ha.passive_eni0_id)
        replace_routes(ha.active_eni1_route_map, ha.passive_eni1_id)
        update_tags(ha.passive_id, ha.active_id)
    elif hcactive.status is False and hcpassive.status is False:
        logger.error('!!-->> Both units are down: Bypassing EIP & route checks')
    logger.info('-=-' * 20)
#
# end of script
#
