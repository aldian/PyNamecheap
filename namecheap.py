import sys
import requests # pip install requests
from xml.etree.ElementTree import fromstring

inPy3k = sys.version_info[0] == 3

# http://developer.namecheap.com/docs/doku.php?id=overview:2.environments
ENDPOINTS = {
	# To use
	# 1) browse to http://www.sandbox.namecheap.com/
	# 2) create account, my account > manage profile > api access > enable API
	# 3) add your IP address to whitelist
	'sandbox' : 'https://api.sandbox.namecheap.com/xml.response',
	'production' : 'https://api.namecheap.com/xml.response',
}
NAMESPACE = "http://api.namecheap.com/xml.response"

# https://www.namecheap.com/support/api/error-codes.aspx
class ApiError(Exception):
	WHOISGUARD_ALREADY_ENABLED = '2011331'

	def __init__(self, number, text):
		Exception.__init__(self, '%s - %s' % (number, text))
		self.number = number
		self.text = text

class Api(object):
	# Follows API spec capitalization in variable names for consistency.
	def __init__(self, ApiUser, ApiKey, UserName, ClientIP, sandbox = True, debug = True):
		self.ApiUser = ApiUser
		self.ApiKey = ApiKey
		self.UserName = UserName
		self.ClientIP = ClientIP
		self.endpoint = ENDPOINTS['sandbox' if sandbox else 'production']
		self.debug = debug

	# https://www.namecheap.com/support/api/methods/domains/create.aspx
	def domains_create(self, DomainName, FirstName, LastName,
		Address1, City, StateProvince, PostalCode, Country, Phone,
		EmailAddress, Address2 = None, years = 1, whoisguardActivated = False):
		"""
		Registers a domain name with the given contact info.
		Example of a working phone number: +81.123123123

		For simplicity assumes one person acts as all contact types."""

		contact_types = ['Registrant', 'Tech', 'Admin', 'AuxBilling']

		extra_payload = {
			'DomainName' : DomainName,
			'years' : years
		}

		for contact_type in contact_types:
			extra_payload.update({
				'%sFirstName' % contact_type : FirstName,
				'%sLastName' % contact_type : LastName,
				'%sAddress1' % contact_type : Address1,
				'%sCity' % contact_type : City,
				'%sStateProvince' % contact_type : StateProvince,
				'%sPostalCode' % contact_type : PostalCode,
				'%sCountry' % contact_type : Country,
				'%sPhone' % contact_type : Phone,
				'%sEmailAddress' % contact_type : EmailAddress,
			})
			if Address2:
				extra_payload['%sAddress2' % contact_type] = Address2

		if whoisguardActivated:
			extra_payload['AddFreeWhoisguard'] = 'yes'
			extra_payload['WGEnabled'] = 'yes'

		self._call('namecheap.domains.create', extra_payload)

		if whoisguardActivated:
			whoisguardID = self.whoisguard_getIdByDomainName(DomainName)
			if whoisguardID:
				try:
					self.whoisguard_enable(whoisguardID, EmailAddress)
				except ApiError as e:
					if e.number != ApiError.WHOISGUARD_ALREADY_ENABLED:
						raise e

	def _payload(self, Command, extra_payload = {}):
		"""Make dictionary for passing to requests.get"""
		payload = {
			'ApiUser' : self.ApiUser,
			'ApiKey' : self.ApiKey,
			'UserName' : self.UserName,
			'ClientIP' : self.ClientIP,
			'Command' : Command,
		}
		payload.update(extra_payload)
		return payload

	def _fetch_xml(self, payload):
		"""Make network call and return parsed XML element"""
		r = requests.post(self.endpoint, params=payload)
		if self.debug:
			print("--- Request ---")
			print(r.url)
			print("--- Response ---")
			print(r.text)
		xml = fromstring(r.text)

		if xml.attrib['Status'] == 'ERROR':
			# Response namespace must be prepended to tag names.
			xpath = './/{%(ns)s}Errors/{%(ns)s}Error' % {'ns' : NAMESPACE}
			error = xml.find(xpath)
			raise ApiError(error.attrib['Number'], error.text)

		return xml

	def _call(self, Command, extra_payload = {}):
		"""Call an API command"""
		payload = self._payload(Command, extra_payload)
		xml = self._fetch_xml(payload)
		return xml

	class LazyGetListIterator(object):
		"""When listing domain names, only one page is returned
		initially. The list needs to be paged through to see all.
		This iterator gets the next page when necessary."""
		def _get_more_results(self):
			xml = self.api._fetch_xml(self.payload)
			domains = xml.findall(self.xpath)
			for domain in domains:
				self.results.append(domain.attrib)
			self.payload['Page'] += 1

		def __init__(self, api, payload, xpath=None):
			self.api = api
			self.payload = payload
			if xpath is None:
				self.xpath = './/{%(ns)s}CommandResponse/{%(ns)s}DomainGetListResult/{%(ns)s}Domain' % {'ns' : NAMESPACE}
			else:
				self.xpath = xpath
			self.results = []
			self.i = -1

		def __iter__(self):
			return self

		def next(self):
			self.i += 1
			if self.i >= len(self.results):
				self._get_more_results()

			if self.i >= len(self.results):
				raise StopIteration
			else:
				return self.results[self.i]

	# https://www.namecheap.com/support/api/methods/domains-dns/set-default.aspx
	def domains_dns_setDefault(self, domain):
		sld, tld = domain.split(".")
		self._call("namecheap.domains.dns.setDefault", {
			'SLD' : sld,
			'TLD' : tld
		})

	# https://www.namecheap.com/support/api/methods/domains/check.aspx
	def domains_check(self, domains):
		"""Checks the availability of domains.

		For example
		api.domains_check(['taken.com', 'apsdjcpoaskdc.com'])

		Might result in
		{
			'taken.com' : False,
			'apsdjcpoaskdc.com' : True
		}
		"""

		# For convenience, allow a single domain to be given
		if not inPy3k:
			if isinstance(domains, basestring):
				return self.domains_check([domains]).items()[0][1]
		else:
			if isinstance(domains, str):
				return list(self.domains_check([domains]).items())[0][1]

		extra_payload = {'DomainList' : ",".join(domains)}
		xml = self._call('namecheap.domains.check', extra_payload)
		xpath = './/{%(ns)s}CommandResponse/{%(ns)s}DomainCheckResult' % {'ns' : NAMESPACE}
		results = {}
		for check_result in xml.findall(xpath):
			results[check_result.attrib['Domain']] = check_result.attrib['Available'] == 'true'
		return results

	@classmethod
	def _tag_without_namespace(cls, element):
		return element.tag.replace("{%s}" % NAMESPACE, "")

	@classmethod
	def _list_of_dictionaries_to_numbered_payload(cls, l):
		"""
		[
			{'foo' : 'bar', 'cat' : 'purr'},
			{'foo' : 'buz'},
			{'cat' : 'meow'}
		]

		becomes

		{
			'foo1' : 'bar',
			'cat1' : 'purr',
			'foo2' : 'buz',
			'cat3' : 'meow'
		}
		"""
		return dict(sum([
			[(k+str(i+1),v) for k,v in d.items()] \
			for i,d in enumerate(l)
		], []))

#y = [dict([(k+str(i+1),v) for k,v in d.items()]) for i,d in enumerate(l)]

	# https://www.namecheap.com/support/api/methods/domains/get-contacts.aspx
	def domains_getContacts(self, DomainName):
		"""Gets contact information for the requested domain.
		There are many categories of contact info, such as admin and billing.

		The returned data is like:
		{
			'Admin' : {'FirstName' : 'John', 'LastName' : 'Connor', ...},
			'Registrant' : {'FirstName' : 'Namecheap.com', 'PhoneExt' : None, ...},
			...
		}
		"""
		xml = self._call('namecheap.domains.getContacts', {'DomainName' : DomainName})
		xpath = './/{%(ns)s}CommandResponse/{%(ns)s}DomainContactsResult/*' % {'ns' : NAMESPACE}
		results = {}
		for contact_type in xml.findall(xpath):
			fields_for_one_contact_type = {}
			for contact_detail in contact_type.findall('*'):
				fields_for_one_contact_type[self._tag_without_namespace(contact_detail)] = contact_detail.text
			results[self._tag_without_namespace(contact_type)] = fields_for_one_contact_type
		return results

	# https://www.namecheap.com/support/api/methods/domains-dns/set-hosts.aspx
	def domains_dns_setHosts(self, domain, host_records):
		"""Sets the DNS host records for a domain.

		Example:

		api.domains_dns_setHosts('example.com', [
			{
				'HostName' : '@',
				'RecordType' : 'URL',
				'Address' : 'http://news.ycombinator.com',
				'MXPref' : '10',
				'TTL' : '100'
			}
		])"""

		extra_payload = self._list_of_dictionaries_to_numbered_payload(host_records)
		sld, tld = domain.split(".")
		extra_payload.update({
			'SLD' : sld,
			'TLD' : tld
		})
		self._call("namecheap.domains.dns.setHosts", extra_payload)

	# https://www.namecheap.com/support/api/methods/domains-dns/set-custom.aspx
	def domains_dns_setCustom(self, domain, host_records):
		"""Sets the domain to use the supplied set of nameservers.

		Example:

		api.domains_dns_setCustom('example.com', { 'Nameservers' : 'ns1.example.com,ns2.example.com' })"""

		extra_payload = host_records
		sld, tld = domain.split(".")
		extra_payload['SLD'] = sld
		extra_payload['TLD'] = tld
		self._call("namecheap.domains.dns.setCustom", extra_payload)

	# https://www.namecheap.com/support/api/methods/domains-dns/get-hosts.aspx
	def domains_dns_getHosts(self, domain):
		"""Retrieves DNS host record settings. Note that the key names are different from those
		you use when setting the host records."""
		sld, tld = domain.split(".")
		extra_payload = {
			'SLD' : sld,
			'TLD' : tld
		}
		xml = self._call("namecheap.domains.dns.getHosts", extra_payload)
		xpath = './/{%(ns)s}CommandResponse/{%(ns)s}DomainDNSGetHostsResult/*' % {'ns' : NAMESPACE}
		results = []
		for host in xml.findall(xpath):
			results.append(host.attrib)
		return results

	# https://www.namecheap.com/support/api/methods/domains-dns/get-list.aspx
	def domains_getList(self, ListType = None, SearchTerm = None, PageSize = None, SortBy = None):
		"""Returns an iterable of dicts. Each dict represents one
		domain name the user has registered, for example
		{
			'Name': 'coolestfriends.com',
			'Created': '04/11/2012',
			'Expires': '04/11/2018',
			'ID': '8385859',
			'AutoRenew': 'false',
			'IsLocked': 'false',
			'User': 'Bemmu',
			'IsExpired': 'false',
			'WhoisGuard': 'NOTPRESENT'
		}
		"""

		# The payload is a dict of GET args that is passed to
		# the lazy-loading iterator so that it can know how to
		# get more results.
		extra_payload = {'Page' : 1}
		if ListType: extra_payload['ListType'] = ListType
		if SearchTerm: extra_payload['SearchTerm'] = SearchTerm
		if PageSize: extra_payload['PageSize'] = PageSize
		if SortBy: extra_payload['SortBy'] = SortBy
		payload = self._payload('namecheap.domains.getList', extra_payload)
		return self.LazyGetListIterator(self, payload)

	# https://www.namecheap.com/support/api/methods/whoisguard/getlist.aspx
	def whoisguard_getList(self, Page = 1, ListType = None, PageSize = None):
		"""
		:return: an iterable of dicts.
		"""
		extra_payload = {'Page' : Page}
		if ListType: extra_payload['ListType'] = ListType
		if PageSize: extra_payload['PageSize'] = PageSize
		payload = self._payload('namecheap.whoisguard.getList', extra_payload)
		return self.LazyGetListIterator(self, payload, xpath='.//{%(ns)s}CommandResponse/{%(ns)s}WhoisguardGetListResult/{%(ns)s}Whoisguard' % {'ns' : NAMESPACE})

	def whoisguard_getIdByDomainName(self, domain):
		whoisguards = self.whoisguard_getList(Page = 1, PageSize = 100)
		try:
			while True:
				whoisguard = whoisguards.next()
				if whoisguard['DomainName'] == domain:
					return whoisguard['ID']
		except StopIteration:
			pass

	def whoisguard_enable(self, WhoisguardID, ForwardedToEmail):
		extra_payload = {
			'WhoisguardID': WhoisguardID,
			'ForwardedToEmail': ForwardedToEmail
		}
		self._call("namecheap.whoisguard.enable", extra_payload)

	def whoisguard_disable(self, WhoisguardID):
		extra_payload = {
			'WhoisguardID': WhoisguardID,
		}
		self._call("namecheap.whoisguard.disable", extra_payload)
