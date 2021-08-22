import subprocess

import click
import boto3
import requests


def get_my_public_ip():
    endpoint = "https://ipinfo.io/json"
    response = requests.get(endpoint, verify=True)
    if response.status_code != 200:
        raise click.ClickException("Unable to get your public ip!")
    data = response.json()
    return data["ip"]


@click.group()
def cli():
    pass


# TODO: add name "novpn-agent" to the instance
# TODO: if instance already exists do not create it
# TODO: if sg already exists do not create it
# TODO: connect with ssh
# TODO: implement stop command: starting from the ssh connection, then delete instance, then delete SG


@cli.command()
@click.option("--region", default=None)
@click.option("--vpc", default=None)
@click.option("--keypair", default=None)
@click.option("--local-port", type=int, default=54321)
@click.argument("local_key_path", type=click.Path(exists=True))
def start(region, vpc, keypair, local_port, local_key_path):
    start_novpn(region, vpc, keypair, local_port, local_key_path)


def start_novpn(region, vpc, keypair, local_port, local_key_path):
    click.echo("Starting novpn agent")
    instances = start_ec2_instance(region, vpc, keypair)
    print(instances)
    print(instances[0].public_ip_address)
    # start_ssh_tunnel(instance_info.address, local_port)
    subprocess.run(
        [
            "ssh",
            "-i",
            f"{local_key_path}",
            "-fN",
            "-D",
            f"{local_port}",
            f"ec2-user@{instances[0].public_ip_address}",
        ]
    )


def get_ami_id(region):
    return "ami-02b4e72b17337d6c1"


def get_key_name(region):
    return "gioruf"


def create_security_group(ec2):
    my_ip = get_my_public_ip()
    security_group = ec2.create_security_group(
        Description="Allow ssh access to novpn instance",
        GroupName="novpn",
    )
    security_group.authorize_ingress(
        IpPermissions=[
            {
                "FromPort": 22,
                "ToPort": 22,
                "IpProtocol": "TCP",
                "IpRanges": [{"CidrIp": f"{my_ip}/32"}],
            }
        ]
    )
    return security_group


def start_ec2_instance(region, vpc, keypair):
    ec2 = boto3.resource("ec2", region_name=region)
    click.echo("Setting up security group")
    security_group = create_security_group(ec2)
    click.echo("Creating ec2 instance")
    instances = ec2.create_instances(
        ImageId=get_ami_id(region),
        InstanceType="t2.micro",
        KeyName=get_key_name(region),
        MinCount=1,
        MaxCount=1,
        SecurityGroupIds=[security_group.id],
    )
    click.echo("Waiting for the ec2 instance to come alive")
    waiter = boto3.client("ec2").get_waiter("instance_status_ok")
    waiter.wait(InstanceIds=[instances[0].id])
    instances[0].reload()
    return instances


def start_ssh_tunnel(ec2_instance_address, local_port):
    pass


if __name__ == "__main__":
    cli()
