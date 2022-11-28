## Description

Deploy a single BYOL FortiGate in AWS using CloudFormation with preconfigured ZTNA settings

## Deployment overview


This deployment requires that you already have the following already configured:

-   A VPC
-   Two subnets - **Public and Private Subnets**
-   Web Server inside the private subnet.  Used for testing ZTNA application access.
-   S3 bucket within the same region where the CFT will deploy in.


Cloudformation deploys the following components:

-   A FortiGate BYOL instance with two NICs, one in each subnet
-   An S3 endpoint inside the public subnet. (Depends on if already existed)
    <sub>S3 endpoint is used for connecting to the S3 bucket via internally.
-   A Lambda function.

## Deployment:

1. Fill in the parameters as shown below:

-   CIDRForInstanceAccess
-   EncryptVolumes
-   FortiOSVersion
-   InitS3Bucket
-   InstanceType
-   KeyPair
-   LicenseType
-   LocalUsername
-   LocalUserPassword
-   PrivateSubnet
-   PrivateSubnetRouterIP
-   PublicSubnet
-   PublicSubnetRouterIP
-   PublicSubnetRouteTableID
-   S3EndpointDeployment
-   ServerName
-   ServerPrivateIP
-   VPCCIDR
-   VPCID
-   ZTNAGatewayLicenseFile
-   ZTNAGatewayPrivateIP
-   ZTNAGatewayPublicIP
-   EMSServerType
-   EMSServerIP
-   EMSServerPort

 ![AWS FortiGate Deploy-1](./parameter-1.png)
 ![AWS FortiGate Deploy-2](./parameter-2.png)
 ![AWS FortiGate Deploy-2](./parameter-3.png)

 2. Continue to deploy the stack.

 3. Outputs.  Provides the URL to login to ZTNAApplication and ZTNAGateway along with the login credential.  It is advised to modifed this once login to the ZTNAGateway

![AWS FortiGate Output](output.png)

## Destroy the stack

To destroy the stack, choose the stack and click on `Delete`

# Support

Fortinet-provided scripts in this and other GitHub projects do not fall under the regular Fortinet technical support scope and are not supported by FortiCare Support Services.
For direct issues, please refer to the [Issues](https://github.com/fortinet/fortigate-terraform-deploy/issues) tab of this GitHub project.
For other questions related to this project, contact [github@fortinet.com](mailto:github@fortinet.com).

## License

[License](https://github.com/fortinet/fortigate-terraform-deploy/blob/master/LICENSE) © Fortinet Technologies. All rights reserved.
