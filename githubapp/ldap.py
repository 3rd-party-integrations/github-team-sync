import os
import traceback
import sys
import json
import logging
import ssl
from ldap3 import Server, Connection, Tls, ALL
from ldap3.utils.conv import escape_filter_chars
from pprint import pprint

LOG = logging.getLogger(__name__)


class LDAPClient:
    def __init__(self):
        # Read settings from the config file and store them as constants
        self.LDAP_SERVER_HOST = os.environ["LDAP_SERVER_HOST"]
        self.LDAP_BASE_DN = os.environ["LDAP_BASE_DN"]
        self.LDAP_USER_BASE_DN = os.environ["LDAP_USER_BASE_DN"]
        self.LDAP_USER_ATTRIBUTE = os.environ["LDAP_USER_ATTRIBUTE"]
        self.LDAP_USER_FILTER = os.environ["LDAP_USER_FILTER"].replace(
            "{ldap_user_attribute}", self.LDAP_USER_ATTRIBUTE
        )
        self.LDAP_USER_MAIL_ATTRIBUTE = os.environ["LDAP_USER_MAIL_ATTRIBUTE"]
        self.LDAP_GROUP_BASE_DN = os.environ["LDAP_GROUP_BASE_DN"]
        self.LDAP_GROUP_FILTER = os.environ["LDAP_GROUP_FILTER"]
        self.LDAP_GROUP_MEMBER_ATTRIBUTE = os.environ["LDAP_GROUP_MEMBER_ATTRIBUTE"]
        if "LDAP_BIND_USER" in os.environ:
            self.LDAP_BIND_USER = os.environ["LDAP_BIND_USER"]
        elif "LDAP_BIND_DN" in os.environ:
            self.LDAP_BIND_USER = os.environ["LDAP_BIND_DN"]
        else:
            raise Exception("LDAP credentials have not been specified")
        if "LDAP_PAGE_SIZE" in os.environ:
            self.LDAP_PAGE_SIZE = os.environ["LDAP_SEARCH_PAGE_SIZE"]
        else:
            self.LDAP_PAGE_SIZE = 1000
        if "LDAP_BIND_PASSWORD" in os.environ:
            self.LDAP_BIND_PASSWORD = os.environ["LDAP_BIND_PASSWORD"]
        else:
            raise Exception("LDAP credentials have not been specified")

        self.USER_SYNC_ATTRIBUTE = os.environ["USER_SYNC_ATTRIBUTE"]

        self.LDAP_USE_SSL = bool(os.environ("LDAP_USE_SSL", False))
        if self.LDAP_USE_SSL:
            self.LDAP_SSL_PRIVATE_KEY = os.environ.get("LDAP_SSL_PRIVATE_KEY")
            self.LDAP_SSL_CERTIFICATE = os.environ.get("LDAP_SSL_CERTIFICATE")
            try:
                self.LDAP_SSL_VALIDATE = ssl.VerifyMode[
                    os.environ.get("LDAP_SSL_VALIDATE", "CERT_REQUIRED")
                ]
            except KeyError:
                raise Exception(
                    f"LDAP_SSL_VALIDATE valid options are {ssl.VerifyMode._member_names_}"
                )
            try:
                self.LDAP_SSL_VERSION = ssl._SSLMethod[
                    os.environ.get("LDAP_SSL_VERSION", "PROTOCOL_TLS")
                ]
            except KeyError:
                raise Exception(
                    f"LDAP_SSL_VERSION valid options are {ssl._SSLMethod._member_names_}"
                )
            self.LDAP_SSL_CA_CERTS = os.environ.get("LDAP_SSL_CA_CERTS")
            self.tls = Tls(
                local_private_key_file=self.LDAP_SSL_PRIVATE_KEY,
                local_certificate_file=self.LDAP_SSL_CERTIFICATE,
                validate=self.LDAP_SSL_VALIDATE,
                version=self.LDAP_SSL_VERSION,
                ca_certs_file=self.LDAP_SSL_CA_CERTS,
            )
        else:
            self.tls = None
        if "LDAP_SERVER_PORT" in os.environ:
            self.LDAP_SERVER_PORT = os.environ["LDAP_SERVER_PORT"]
        else:
            if self.LDAP_USE_SSL:
                self.LDAP_SERVER_PORT = 636
            else:
                self.LDAP_SERVER_PORT = 389

        self.srv = Server(
            host=self.LDAP_SERVER_HOST,
            port=self.LDAP_SERVER_PORT,
            use_ssl=self.USE_SSL,
            tls=self.tls,
        )
        self.conn = Connection(
            self.srv,
            user=self.LDAP_BIND_USER,
            password=self.LDAP_BIND_PASSWORD,
            auto_bind=True,
            auto_range=True,
        )

    def get_group_members(self, group_name):
        """
        Get members of the requested group in LDAP/Active Directory
        :param group_name: The name of the group
        :type group_name: str
        :return member_list: List of members found in this LDAP group
        :rtype member_list: list
        """
        member_list = []
        entries = self.conn.extend.standard.paged_search(
            search_base=self.LDAP_BASE_DN,
            search_filter=self.LDAP_GROUP_FILTER.replace("{group_name}", group_name),
            attributes=[self.LDAP_GROUP_MEMBER_ATTRIBUTE],
            paged_size=self.LDAP_PAGE_SIZE,
        )
        for entry in entries:
            if entry["type"] == "searchResEntry":
                for member in entry["attributes"][self.LDAP_GROUP_MEMBER_ATTRIBUTE]:
                    if self.LDAP_GROUP_BASE_DN in member:
                        pass
                    # print("Nested groups are not yet supported.")
                    # print("This feature is currently under development.")
                    # print("{} was not processed.".format(member))
                    # print("Unable to look up '{}'".format(member))
                    # print(e)
                    else:
                        try:
                            member_dn = self.get_user_info(user=member)
                            # pprint(member_dn)
                            if (
                                member_dn
                                and member_dn["attributes"]
                                and member_dn["attributes"][self.LDAP_USER_ATTRIBUTE]
                            ):
                                username = str(
                                    member_dn["attributes"][self.LDAP_USER_ATTRIBUTE][0]
                                ).casefold()
                                if (
                                    self.USER_SYNC_ATTRIBUTE == "mail"
                                    and self.LDAP_USER_MAIL_ATTRIBUTE
                                    not in member_dn["attributes"]
                                ):
                                    raise Exception(
                                        f"{self.USER_SYNC_ATTRIBUTE} not found"
                                    )
                                elif (
                                    self.LDAP_USER_MAIL_ATTRIBUTE
                                    in member_dn["attributes"]
                                ):
                                    email = str(
                                        member_dn["attributes"][
                                            self.LDAP_USER_MAIL_ATTRIBUTE
                                        ][0]
                                    ).casefold()
                                else:
                                    email = None
                                if "EMU_SHORTCODE" in os.environ:
                                    username = (
                                        username + "_" + os.environ["EMU_SHORTCODE"]
                                    )
                                user_info = {"username": username, "email": email}
                                member_list.append(user_info)
                        except Exception as e:
                            traceback.print_exc(file=sys.stderr)
        return member_list

    def get_user_info(self, user=None):
        """
        Look up user info from LDAP
        :param user:
        :type user:
        :return:
        :rtype:
        """
        if any(attr in user.casefold() for attr in ["uid=", "cn="]):
            search_base = user
        else:
            search_base = self.LDAP_USER_BASE_DN
        try:
            try:
                self.conn.search(
                    search_base=search_base,
                    search_filter=self.LDAP_USER_FILTER.replace(
                        "{username}", escape_filter_chars(user)
                    ),
                    attributes=["*"],
                )
                if len(self.conn.entries) > 0:
                    data = json.loads(self.conn.entries[0].entry_to_json())
                    return data
            except Exception as e:
                traceback.print_exc(file=sys.stderr)
        except Exception as e:
            traceback.print_exc(file=sys.stderr)
