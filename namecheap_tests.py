# Run "nosetests" on command line to run these.
import sys
from namecheap import Api, ApiError
from nose.tools import * # pip install nose

api_key = '' # You create this on Namecheap site
username = ''
ip_address = '' # Your IP address that you whitelisted on the site

# If you prefer, you can put the above in credentials.py instead
try:
	from credentials import api_key, username, ip_address
except:
	pass

def random_domain_name():
	import random, time
	domain_name = "%s%s.com" % (int(time.time()), random.randint(0,10**16))
	return domain_name

def test_credentials_not_empty():
	assert_not_equal('', username.strip)
	assert_not_equal('', api_key.strip)
	assert_not_equal('', ip_address.strip)

def test_domain_taken():
	api = Api(username, api_key, username, ip_address, sandbox = True)
	domain_name = "google.com"
	assert_equal(api.domains_check(domain_name), False)

def test_domain_available():
	api = Api(username, api_key, username, ip_address, sandbox = True)
	domain_name = random_domain_name()
	assert_equal(api.domains_check(domain_name), True)

def test_register_domain():
	api = Api(username, api_key, username, ip_address, sandbox = True)

	# Try registering a random domain. Fails if exception raised.
	domain_name = random_domain_name()
	api.domains_create(
		DomainName = domain_name,
		FirstName = 'Jack',
		LastName = 'Trotter',
		Address1 = 'Ridiculously Big Mansion, Yellow Brick Road',
		City = 'Tokushima',
		StateProvince = 'Tokushima',
		PostalCode = '771-0144',
		Country = 'Japan',
		Phone = '+81.123123123',
		EmailAddress = 'jack.trotter@example.com'
	)
	return domain_name

def test_domains_getList():
	api = Api(username, api_key, username, ip_address, sandbox = True)
	api.domains_getList()

@raises(ApiError)
def test_domains_dns_setDefault_on_nonexisting_domain():
	api = Api(username, api_key, username, ip_address, sandbox = True)

	domain_name = random_domain_name()

	# This should fail because the domain does not exist
	api.domains_dns_setDefault(domain_name)	

def test_domains_dns_setDefault_on_existing_domain():
	api = Api(username, api_key, username, ip_address, sandbox = True)
	domain_name = test_register_domain()
	api.domains_dns_setDefault(domain_name)	

def test_domains_getContacts():
	# How would I test for this? This needs a known registered
	# domain to get the contact info for, but in sandbox won't
	# have any.
	pass

def test_domains_dns_setHosts():
	api = Api(username, api_key, username, ip_address, sandbox = True)
	domain_name = test_register_domain()
	api.domains_dns_setHosts(
		domain_name,
		[{
			'HostName' : '@',
			'RecordType' : 'URL',
			'Address' : 'http://news.ycombinator.com',
			'MXPref' : '10',
			'TTL' : '100'
		}]
	)

#
# I wasn't able to get this to work on any public name servers that I tried
# including the ones used in their own example:
#   dns1.name-servers.com
#   dns2.name-server.com
# Using my own Amazon Route53 name servers the test works fine but I didn't
# want to embed my own servers
# Adjust the name servers below to your own and uncomment the test to run

#def test_domains_dns_setCustom():
#	api = Api(username, api_key, username, ip_address, sandbox = True)
#	domain_name = test_register_domain()
#	result = api.domains_dns_setCustom(
#		domain_name, { 'Nameservers' : 'ns1.google.com,ns2.google.com' }
#	)

def test_domains_dns_getHosts():
	api = Api(username, api_key, username, ip_address, sandbox = True)
	domain_name = test_register_domain()
	api.domains_dns_setHosts(
		domain_name,
		[{
			'HostName' : '@',
			'RecordType' : 'URL',
			'Address' : 'http://news.ycombinator.com',
			'MXPref' : '10',
			'TTL' : '100'
		},
		{
			'HostName' : '*',
			'RecordType' : 'A',
			'Address' : '1.2.3.4',
			'MXPref' : '10',
			'TTL' : '1800'
		}]
	)

	hosts = api.domains_dns_getHosts(domain_name)

	# these might change
	del hosts[0]['HostId'] 
	del hosts[1]['HostId'] 

	expected_result = [{'Name': '*', 'Address': '1.2.3.4', 'TTL': '1800', 'Type': 'A', 'MXPref': '10', 'AssociatedAppTitle': '', 'FriendlyName': '', 'IsActive': ''}, {'Name': '@', 'Address': 'http://news.ycombinator.com', 'TTL': '100', 'Type': 'URL', 'MXPref': '10', 'AssociatedAppTitle': '', 'FriendlyName': '', 'IsActive': ''}]
	assert_equal(hosts, expected_result)

def test_list_of_dictionaries_to_numbered_payload():
	x = [
		{'foo' : 'bar', 'cat' : 'purr'},
		{'foo' : 'buz'},
		{'cat' : 'meow'}
	]

	result = Api._list_of_dictionaries_to_numbered_payload(x)

	expected_result = {
		'foo1' : 'bar',
		'cat1' : 'purr',
		'foo2' : 'buz',
		'cat3' : 'meow'
	}

	assert_equal(result, expected_result)


def test_whoisguard_getList():
	# Comment the return statement below to let this test case run
	return
	api = Api(username, api_key, username, ip_address, sandbox = False)
	#api.debug = False
	whoisguard_list = api.whoisguard_getList(Page=1, PageSize=20)
	try:
		i = 1
		while True:
			whoisguard = whoisguard_list.next()
			print("WHOISGUARD: ", i, whoisguard['ID'], whoisguard['DomainName'], file=sys.stderr)
			i += 1
	except StopIteration as e:
		pass


def test_whoisguard_getIdByDomainName():
	# Comment the return statement below to let this test case run
	return
	api = Api(username, api_key, username, ip_address, sandbox = False)
	api.debug = False
	#whoisguardId = api.whoisguard_getIdByDomainName('banteg.tech')
	#whoisguardId = api.whoisguard_getIdByDomainName('kampret.site')
	whoisguardId = api.whoisguard_getIdByDomainName('kingkong.site')
	#assert_equal('15558880', whoisguardId)
	assert_equal('15570269', whoisguardId)


def test_whoisguard_enable():
	# Comment the return statement below to let this test case run
	return
	api = Api(username, api_key, username, ip_address, sandbox = False)
	api.debug = False
	try:
		xml = api.whoisguard_enable('15558880', 'aldian.f@gmail.com')
		print("XML:", xml, file=sys.stderr)
	except ApiError as e:
		print("e: ", e.number, type(e.number), file=sys.stderr)
		if e.number != '2011331':
			raise e

def test_whoisguard_disable():
	# Comment the return statement below to let this test case run
	return
	api = Api(username, api_key, username, ip_address, sandbox = False)
	#api.debug = False
	xml = api.whoisguard_disable('15558880')
	print("XML:", xml, file=sys.stderr)

def test_domains_create_with_whoisguard():
	# Comment the return statement below to let this test case run
	return
	api = Api(username, api_key, username, ip_address, sandbox = False)
	#api.debug = False
	api.domains_create(
		#DomainName = 'kampret.site',
		DomainName = 'kingkong.site',
		FirstName = 'Jack',
		LastName = 'Trotter',
		Address1 = 'Ridiculously Big Mansion, Yellow Brick Road',
		City = 'Tokushima',
		StateProvince = 'Tokushima',
		PostalCode = '771-0144',
		Country = 'Japan',
		Phone = '+81.123123123',
		EmailAddress = 'aldian.f@gmail.com',
		whoisguardActivated = True,
	)


test_whoisguard_getList.whoisguard = 1
test_whoisguard_getIdByDomainName.whoisguard = 1
test_whoisguard_enable.whoisguard = 1
test_whoisguard_disable.whoisguard = 1
test_domains_create_with_whoisguard.whoisguard = 1
#nosetests -a 'whoisguard'
