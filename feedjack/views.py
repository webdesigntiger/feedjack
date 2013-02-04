# -*- coding: utf-8 -*-


from django.utils import feedgenerator
from django.shortcuts import render_to_response
from django.http import HttpResponse, Http404, HttpResponsePermanentRedirect
from django.utils.cache import patch_vary_headers
from django.template import Context, RequestContext, loader
from django.views.generic.simple import redirect_to
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from django.utils.encoding import smart_unicode
from django.views.decorators.http import condition

from feedjack import models, fjlib, fjcache

import itertools as it, operator as op, functools as ft
from datetime import datetime
from collections import defaultdict
from urlparse import urlparse


def cache_etag(request, *argz, **kwz):
	'''Produce etag value for a cached page.
		Intended for usage in conditional views (@condition decorator).'''
	response, site, cachekey = initview(request)
	if not response: return None
	return fjcache.str2md5(
		'{0}--{1}--{2}'.format( site.id if site else 'x', cachekey,
			response[1].strftime('%Y-%m-%d %H:%M:%S%z') ) )

def cache_last_modified(request, *argz, **kwz):
	'''Last modification date for a cached page.
		Intended for usage in conditional views (@condition decorator).'''
	response, site, cachekey = initview(request)
	if not response: return None
	return response[1]


def initview(request, response_cache=True):
	'''Retrieves the basic data needed by all feeds (host, feeds, etc)
		Returns a tuple of:
			1. A valid cached response or None
			2. The current site object
			3. The cache key
			4. The subscribers for the site (objects)
			5. The feeds for the site (ids)'''

	http_host, path_info = ( smart_unicode(part.strip('/')) for part in
		[ request.META['HTTP_HOST'],
			request.META.get('REQUEST_URI', request.META.get('PATH_INFO', '/')) ] )
	query_string = request.META['QUERY_STRING']

	url = '{0}/{1}'.format(http_host, path_info)
	cachekey = u'{0}?{1}'.format(*it.imap(smart_unicode, (path_info, query_string)))
	hostdict = fjcache.hostcache_get() or dict()

	if url in hostdict:
		site = models.Site.objects.get(pk=hostdict[url])

	else:
		sites = list(models.Site.objects.all())

		if not sites:
			# Somebody is requesting something, but the user
			#  didn't create a site yet. Creating a default one...
			site = models.Site(
				name='Default Feedjack Site/Planet',
				url=request.build_absolute_uri(request.path),
				title='Feedjack Site Title',
				description='Feedjack Site Description.'
					' Please change this in the admin interface.',
				template='bootstrap' )
			site.save()

		else:
			# Select the most matching site possible,
			#  preferring "default" when everything else is equal
			results = defaultdict(list)
			for site in sites:
				relevance, site_url = 0, urlparse(site.url)
				if site_url.netloc == http_host: relevance += 10 # host matches
				if path_info.startswith(site_url.path.strip('/')): relevance += 10 # path matches
				if site.default_site: relevance += 5 # marked as "default"
				results[relevance].append((site_url, site))
			for relevance in sorted(results, reverse=True):
				try: site_url, site = results[relevance][0]
				except IndexError: pass
				else: break
			if site_url.netloc != http_host: # redirect to proper site hostname
				response = HttpResponsePermanentRedirect(
					'http://{0}/{1}{2}'.format( site_url.netloc, path_info,
						'?{0}'.format(query_string) if query_string.strip() else '') )
				return (response, timezone.now()), None, cachekey

		hostdict[url] = site.id
		fjcache.hostcache_set(hostdict)

	if response_cache:
		response = fjcache.cache_get(site.id, cachekey)
		if response: return response, None, cachekey

	return None, site, cachekey


def redirect(request, url, **kwz):
	'''Simple redirect, taking site prefix into account,
		otherwise similar to redirect_to generic view.'''
	response, site, cachekey = initview(request)
	if response: return response[0]
	return redirect_to(request, url=site.url + url, **kwz)


def blogroll(request, btype):
	'View that handles the generation of blogrolls.'
	response, site, cachekey = initview(request)
	if response: return response[0]

	template = loader.get_template('feedjack/{0}.xml'.format(btype))
	ctx = dict()
	fjlib.get_extra_content(site, ctx)
	ctx = Context(ctx)
	response = HttpResponse(
		template.render(ctx), mimetype='text/xml; charset=utf-8' )

	patch_vary_headers(response, ['Host'])
	fjcache.cache_set(
		site, cachekey, (response, ctx['last_modified']) )
	return response


def foaf(request):
	'View that handles the generation of the FOAF blogroll.'
	return blogroll(request, 'foaf')


def opml(request):
	'View that handles the generation of the OPML blogroll.'
	return blogroll(request, 'opml')


@condition( etag_func=cache_etag,
	last_modified_func=cache_last_modified )
def buildfeed(request, feedclass, **criterias):
	'View that handles the feeds.'
	# TODO: quite a mess, can't it be handled with a default feed-vews?
	response, site, cachekey = initview(request)
	if response: return response[0]

	feed_title = site.title
	if criterias.get('feed_id'):
		try:
			feed_title = u'{0} - {1}'.format(
				models.Feed.objects.get(id=criterias['feed_id']).title, feed_title )
		except ObjectDoesNotExist: raise Http404 # no such feed
	object_list = fjlib.get_page(site, page=1, **criterias).object_list

	feed = feedclass( title=feed_title, link=site.url,
		description=site.description, feed_url=u'{0}/{1}'.format(site.url, '/feed/rss/') )
	last_modified = datetime(1970, 1, 1, 0, 0, 0, 0, timezone.utc)
	for post in object_list:
		feed.add_item(
			title = u'{0}: {1}'.format(post.feed.name, post.title),
			link = post.link,
			description = fjlib.html_cleaner(post.content),
			author_email = post.author_email,
			author_name = post.author,
			pubdate = post.date_modified,
			unique_id = post.link,
			categories = [tag.name for tag in post.tags.all()] )
		if post.date_updated > last_modified: last_modified = post.date_updated

	response = HttpResponse(mimetype=feed.mime_type)

	# Per-host caching
	patch_vary_headers(response, ['Host'])

	feed.write(response, 'utf-8')
	if site.use_internal_cache:
		fjcache.cache_set(
			site, cachekey, (response, last_modified) )
	return response


def rssfeed(request, **criterias):
	'Generates the RSS2 feed.'
	return buildfeed(request, feedgenerator.Rss201rev2Feed, **criterias)

def atomfeed(request, **criterias):
	'Generates the Atom 1.0 feed.'
	return buildfeed(request, feedgenerator.Atom1Feed, **criterias)


@condition( etag_func=cache_etag,
	last_modified_func=cache_last_modified )
def mainview(request, **criterias):
	'View that handles all page requests.'
	response, site, cachekey = initview(request)

	if not response:
		ctx = fjlib.page_context(request, site, **criterias)
		response = render_to_response(
			u'feedjack/{0}/post_list.html'.format(site.template),
			ctx, context_instance=RequestContext(request) )
		# per host caching, in case the cache middleware is enabled
		patch_vary_headers(response, ['Host'])
		if site.use_internal_cache:
			fjcache.cache_set(
				site, cachekey, (response, ctx['last_modified']) )
	else: response = response[0]

	return response
