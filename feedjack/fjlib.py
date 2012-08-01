# -*- coding: utf-8 -*-


from django.conf import settings
from django.db import connection
from django.core.exceptions import ObjectDoesNotExist
from django.core.paginator import Paginator, InvalidPage
from django.http import Http404
from django.utils.encoding import smart_unicode, force_unicode
from django.utils import timezone

from feedjack import models, fjcache

import itertools as it, operator as op, functools as ft
from collections import OrderedDict
from datetime import datetime, timedelta
from urllib import quote


try:
	from lxml.html import fromstring as lxml_fromstring, tostring as lxml_tostring
	from lxml.html.clean import Cleaner as lxml_Cleaner
	from lxml.etree import XMLSyntaxError as lxml_SyntaxError

except ImportError:
	# at least strip c0 control codes, which are quite common in broken html
	_xml_c0ctl_chars = bytearray(
		set(it.imap(chr, xrange(32)))\
			.difference('\x09\x0a\x0d').union('\x7f'))
	_xml_c0ctl_trans = dict(it.izip(
		_xml_c0ctl_chars, u'_'*len(_xml_c0ctl_chars) ))

	def html_cleaner(string):
		'Produces template-safe valid xml-escaped string.'
		return force_unicode(string).translate(_xml_c0ctl_trans)

	def lxml_fail(string):
		import lxml
		raise NotImplementedError('Looks like some of lxml imports has failed')
	lxml_tostring = lxml_soup = lxml_fail

else:
	def lxml_soup(string):
		'Safe processing of any tag soup (which is a norm on the internets).'
		try: doc = lxml_fromstring(force_unicode(string))
		except lxml_SyntaxError: # last resort for "tag soup"
			from lxml.html.soupparser import fromstring as soup
			doc = soup(force_unicode(string))
		return doc

	def html_cleaner(string):
		'str -> str, like lxml.html.clean.clean_html, but removing styles as well.'
		doc = lxml_soup(string)
		lxml_Cleaner(style=True)(doc)
		return lxml_tostring(doc)


def getquery(query):
	'Performs a query and get the results.'
	try:
		conn = connection.cursor()
		conn.execute(query)
		data = conn.fetchall()
		conn.close()
	except: data = list()
	return data


def get_extra_content(site, ctx):
	'Returns extra data useful to the templates.'
	# Get the subscribers' feeds.
	feeds = site.active_feeds
	ctx['feeds'] = feeds.order_by('name')
	# Get the last_modified/checked time.
	mod, chk = op.itemgetter('modified', 'checked')(feeds.timestamps)
	chk = chk or datetime(1970, 1, 1, 0, 0, 0, 0, timezone.utc)
	ctx['last_modified'], ctx['last_checked'] = mod or chk, chk
	ctx['site'] = site
	# media_url is set here for historical reasons,
	#  please use static_url or STATIC_URL (from django context) in any new templates.
	ctx['media_url'] = ctx['static_url'] =\
		'{}feedjack/{}'.format(settings.STATIC_URL, site.template)


def get_posts_tags(subscribers, object_list, feed, tag_name):
	'''Adds a qtags property in every post object in a page.
		Use "qtags" instead of "tags" in templates to avoid unnecesary DB hits.'''

	tagd = dict()
	user_obj = None
	tag_obj = None
	tags = models.Tag.objects.extra(
		select=dict(post_id='{0}.{1}'.format(
			*it.imap( connection.ops.quote_name,
				('feedjack_post_tags', 'post_id') ) )),
		tables=['feedjack_post_tags'],
		where=[
		'{0}.{1}={2}.{3}'.format(*it.imap( connection.ops.quote_name,
			('feedjack_tag', 'id', 'feedjack_post_tags', 'tag_id') )),
		'{0}.{1} IN ({2})'.format(
			connection.ops.quote_name('feedjack_post_tags'),
			connection.ops.quote_name('post_id'),
			', '.join([str(post.id) for post in object_list]) ) ] )

	for tag in tags:
		if tag.post_id not in tagd: tagd[tag.post_id] = list()
		tagd[tag.post_id].append(tag)
		if tag_name and tag.name == tag_name: tag_obj = tag

	subd = dict()
	for sub in subscribers: subd[sub.feed.id] = sub
	for post in object_list:
		if post.id in tagd: post.qtags = tagd[post.id]
		else: post.qtags = list()
		post.subscriber = subd[post.feed.id]
		if feed == post.feed: user_obj = post.subscriber

	return user_obj, tag_obj


_since_formats = {'%Y-%m-%d', '%Y-%m-%d %H:%M', '%d.%m.%Y'}
_since_formats_vary = ('%Y', '%y'), ('%d', '%a'),\
	('%d', '%A'), ('%m', '%b'), ('%m', '%B')
_since_offsets = {
	'yesterday': 1, 'week': 7, 'month': 30,
	'10_days': 10, '30_days': 30 }

def get_page(site, page=1, **criterias):
	'Returns a paginator object and a requested page from it.'
	global _since_formats_vary

	if 'since' in criterias:
		since = criterias['since']
		if since in _since_offsets:
			since = datetime.today() - timedelta(_since_offsets[since])
		else:
			if _since_formats_vary:
				for fmt, substs in it.product( list(_since_formats),
						it.chain.from_iterable(
							it.combinations(_since_formats_vary, n)
							for n in xrange(1, len(_since_formats_vary)) ) ):
					for src, dst in substs: fmt = fmt.replace(src, dst)
					_since_formats.add(fmt)
				_since_formats_vary = None # to avoid doing it again
			for fmt in _since_formats:
				try: since = datetime.strptime(since, fmt)
				except ValueError: pass
				else: break
			else: raise Http404 # invalid format
		try:
			criterias['since'] = timezone.make_aware(
				since, timezone.get_current_timezone() )
		except (
				timezone.pytz.exceptions.AmbiguousTimeError
				if timezone.pytz else RuntimeError ):
			# Since there's no "right" way here anyway...
			criterias['since'] = since.replace(tzinfo=timezone)
	order_force = criterias.pop('asc', None)

	posts = models.Post.objects.filtered(site, **criterias)\
		.sorted(site.order_posts_by, force=order_force).select_related()

	paginator = Paginator(posts, site.posts_per_page)
	try: return paginator.page(page)
	except InvalidPage: raise Http404


def page_context(request, site, **criterias):
	'Returns the context dictionary for a page view.'
	try: page = int(request.GET.get('page', 1))
	except ValueError: page = 1

	feed, tag = criterias.get('feed'), criterias.get('tag')
	if feed:
		try: feed = models.Feed.objects.get(id=feed)
		except ObjectDoesNotExist: raise Http404

	page = get_page(site, page=page, **criterias)
	subscribers = site.active_subscribers

	if site.show_tagcloud and page.object_list:
		from feedjack import fjcloud
		# This will hit the DB once per page instead of once for every post in
		# a page. To take advantage of this the template designer must call
		# the qtags property in every item, instead of the default tags
		# property.
		user_obj, tag_obj = get_posts_tags(
			subscribers, page.object_list, feed, tag )
		tag_cloud = fjcloud.getcloud(site, feed.id)
	else:
		tag_obj, tag_cloud = None, tuple()
		try:
			user_obj = models.Subscriber.objects\
				.get(site=site, feed=feed) if feed else None
		except ObjectDoesNotExist: raise Http404

	ctx = dict(
		last_modified = max(it.imap(
				op.attrgetter('date_updated'), page.object_list ))\
			if len(page.object_list) else datetime(1970, 1, 1, 0, 0, 0, 0, timezone.utc),

		object_list = page.object_list,
		subscribers = subscribers,
		tag = tag_obj,
		tagcloud = tag_cloud,

		feed = feed,
		url_suffix = ''.join((
			'/feed/{0}'.format(feed.id) if feed else '',
			'/tag/{0}'.format(quote(tag)) if tag else '' )),

		p = page, # "page" is taken by legacy number
		p_10neighbors = OrderedDict(
			# OrderedDict of "num: exists" values
			# Use as "{% for p_num, p_exists in p_10neighbors.items|slice:"7:-7" %}"
			(p, p >= 1 and p <= page.paginator.num_pages)
			for p in ((page.number + n) for n in xrange(-10, 11)) ),

		## DEPRECATED:

		# Totally misnamed and inconsistent b/w user/user_obj,
		#  use "feed" and "subscribers" instead.
		user_id = feed and feed.id,
		user = user_obj,

		# Legacy flat pagination context, use "p" instead.
		is_paginated = page.paginator.num_pages > 1,
		results_per_page = site.posts_per_page,
		has_next = page.has_next(),
		has_previous = page.has_previous(),
		page = page.number,
		next = page.number + 1,
		previous = page.number - 1,
		pages = page.paginator.num_pages,
		hits = page.paginator.count )

	get_extra_content(site, ctx)

	return ctx
