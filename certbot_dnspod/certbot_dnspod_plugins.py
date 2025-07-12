import json
import hashlib
import sys
import random
from datetime import datetime
import os
from typing import Dict, List
from dataclasses import dataclass
from hmac import HMAC
from urllib.request import urlopen, Request

from certbot import errors
from certbot.plugins import dns_common
from tencentcloud.common import credential
from tencentcloud.dnspod.v20210323 import dnspod_client, models


class Authenticator(dns_common.DNSAuthenticator):
    """DNS Authenticator for TencentCloud

    This Authenticator uses the Dnspod API to fulfill a challenge.
    """

    description = (
        "Obtain certificates using a DNS TXT record (if you are "
        "using Dnspod for DNS)."
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.secret_id = None
        self.secret_key = None
        self.cleanup_maps = {}
        self.cred =  None
        self.client = None


    @classmethod
    def add_parser_arguments(cls, add):  # pylint: disable=arguments-differ
        super(Authenticator, cls).add_parser_arguments(add)
        add(
            "credentials",
            help="Dnspod credentials INI file. If omitted, the environment variables TENCENTCLOUD_SECRET_ID and TENCENTCLOUD_SECRET_KEY will be tried",
        )
        add(
            "debug",
            help="turn on debug mode (print some debug info)",
            type=bool,
            default=False,
        )

    # pylint: disable=no-self-use
    def more_info(self):  # pylint: disable=missing-function-docstring
        return (
            "This plugin configures a DNS TXT record to respond to a challenge using "
            + "the Dnspod API."
        )

    def _validate_credentials(self, credentials):
        self.chk_exist(credentials, "secret_id")
        self.chk_exist(credentials, "secret_key")

    def chk_exist(self, credentials, arg):
        v = credentials.conf(arg)
        if not v:
            raise errors.PluginError("{} is required".format(arg))

    def chk_environ_exist(self, arg):
        if os.environ.get(arg) is None:
            print(os.environ)
            raise errors.PluginError("The environment {} is required".format(arg))

    def chk_base_domain(self, base_domain, validation_name):
        if not validation_name.endswith("." + base_domain):
            raise errors.PluginError(
                "validation_name not ends with base domain name, please report to dev. "
                f"real_domain: {base_domain}, validation_name: {validation_name}"
            )

    def determine_base_domain(self, domain, client):
        if self.conf("debug"):
            print("finding base domain")
        domain_list_request = models.DescribeDomainListRequest()
        domain_list_response = client.DescribeDomainList(domain_list_request)
        domain_list = [
            info.Name for info in domain_list_response.DomainList 
        ]
        segments = domain.split(".")
        tried = []
        i = len(segments) - 2
        while i >= 0:
            dt = ".".join(segments[i:])
            tried.append(dt)
            i -= 1
            if dt in domain_list:
                return dt
        raise errors.PluginError(
            "failed to determine base domain, it seems that you dont have any domain of these on Dnspod. " f"Tried: {tried}"
        )
    def determain_rec_line_of_base(self, domain, client):
        req = models.DescribeRecordLineCategoryListRequest()
        req.Domain = domain
        resp = client.DescribeRecordLineCategoryList(req)
        line_list = resp.LineList
        line_infos = [ (line.LineName, line.LineId) for line in line_list ]
        for line_name, line_id in line_infos:
            if line_id == "0": return line_name, line_id
        
        return line_infos[0]
    
    def _setup_credentials(self):
        if self.conf("credentials"):
            credentials = self._configure_credentials(
                "credentials",
                "TencentCloud credentials INI file",
                None,
                self._validate_credentials,
            )
            self.secret_id = credentials.conf("secret_id")
            self.secret_key = credentials.conf("secret_key")
        else:
            self.chk_environ_exist("TENCENTCLOUD_SECRET_ID")
            self.chk_environ_exist("TENCENTCLOUD_SECRET_KEY")
            self.secret_id = os.environ.get("TENCENTCLOUD_SECRET_ID")
            self.secret_key = os.environ.get("TENCENTCLOUD_SECRET_KEY")

        self.cred =  credential.Credential(
            self.secret_id,
            self.secret_key
        )
        self.client = dnspod_client.DnspodClient(credential=self.cred, region = None)



    
    def _perform(self, domain, validation_name, validation):
        if self.conf("debug"):
            print("perform", domain, validation_name, validation)
        try:
            base_domain = self.determine_base_domain(domain, self.client)
            print(f"Determained basedomain: {base_domain}")
            target_line_name, target_line_id = self.determain_rec_line_of_base(base_domain, self.client)
            print(f"Determained validation_name: {validation_name}")
            sub_domain = validation_name[: -(len(base_domain) + 1)]
            print(f"Determained sub_domain: {sub_domain}")
            create_record_req = models.CreateTXTRecordRequest()
            create_record_req.Domain = base_domain
            create_record_req.SubDomain = sub_domain
            create_record_req.Value = validation
            create_record_req.RecordLine = target_line_name
            # r = client.create_record(base_domain, sub_domain, "TXT", validation)
            resp = self.client.CreateTXTRecord(create_record_req)

            self.cleanup_maps[validation_name] = (base_domain, resp.RecordId)
        except  Exception as e:

            raise errors.PluginError(
                f"failed to apply TXT record, please contact developer shanyixiang@gmail.com. -< {e} >- "
            )
            pass     
    def delete_record(self, domain, record_id, client):
        del_record_req = models.DeleteRecordRequest()
        del_record_req.Domain = domain
        del_record_req.RecordId = record_id
        resp = client.DeleteRecord(del_record_req)
        return
    def _cleanup(self, domain, validation_name, validation):
        if self.conf("debug"):
            print("cleanup", domain, validation_name, validation)
        cred =  credential.Credential(
            self.secret_id,
            self.secret_key
        )
        # client = dnspod_client.DnspodClient(credential=cred, region = None)
        if validation_name in self.cleanup_maps:
            base_domain, record_id = self.cleanup_maps[validation_name]
            try:
                self.delete_record(base_domain, record_id, self.client)
            except Exception as e:
                raise errors.PluginError(
                    f"failed to Delete TXT record, please contact developer shanyixiang@gmail.com. -< {e} >- "
                )
        else:
            print("record id not found during cleanup, cleanup probably failed")


