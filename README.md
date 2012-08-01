Intro (original feedjack).
--------------------

Feedjack is a feed aggregator writen in Python using the Django web development
framework.

Like the Planet feed aggregator:

* It downloads feeds and aggregate their contents in a single site
* The new aggregated site has a feed of its own (atom and rss)
* It uses Mark Pilgrim’s excelent FeedParser
* The subscribers list can be exported as OPML and FOAF

Original FeedJack also has some advantages:

* Handles historical data, you can read old posts
* Parses a lot more info, including post categories
* Generates pages with posts of a certain category
* Generates pages with posts from a certain subscriber
* Generates pages with posts of a certain category from a certain subcriber
* A cloud tag/folksonomy (hype 2.0 compliant) for every page and every
  subscriber
* Uses Django templates
* The administration is done via web (using Django's kickass autogenerated
  and magical admin site), and can handle multiple planets
* Extensive use of Django’s cache system. Most of the time you will have no
  database hits when serving pages.

[Original feedjack](http://www.feedjack.org/) project looks abandoned though -
no real updates since 2008 (with quite a lively history before that).

Feedparser itself isn't in much better shape, for that matter - releases weren't
a frequent thing there up to 2011 (svn looked a bit more alive though), but then
Mark Pilgrim pulled out from the internets (4 October 2011), so guess it will
get worse unless someone picks up the development.
It's purpose is fairly simple though and feed formats haven't really changed
since 2005, so it's not so bad yet.
Feel free to update this paragraph if there are now more-or-less mainstream
forks.


Fork
--------------------

* (fixed) Bugs:
	* hashlib warning
	* field lenghts
	* non-unique date sort criteria
	* Always-incorrect date_modified setting (by treating UTC as localtime)
	* Misc unicode handling fixes.

* Features:

	* Proper transactional updates, so single feed failure is guaranteed not to
		produce inconsistency or crash the parser.

	* Simple individual Post filters, built in python (callable, accepting Post
		object and optional parameters, returning True/False), attached (to individual
		Feeds) and configured (additional parameters to pass) via database (or admin
		interface).

	* As complex as needed cross-referencing filters for tasks like site-wide
		elimination of duplicate entries from a different feeds (by arbitrary
		comparison functions as well), and automatic mechanism for invalidation of
		their results.

	* Sane, configurable logging in feedjack_update, without re-inventing the wheel
		via encode, prints and a tons of if's.

	* Ability to use adaptive feed-check interval, based on average feed activity,
		so feeds that get updated once a year won't be polled every hour.

	* "immutable" flag for feeds, so their posts won't be re-fetched if their
		content or date changes (for feeds that have "commets: N" thing).

	* Dropped a chunk of obsolete code (ripped from old Django) - ObjectPaginator in
		favor of native Paginator.

	* Minimalistic "fern" and "plain" (merged from [another
		fork](http://git.otfbot.org/feedjack.git/)) styles, image feed oriented
		"fern_grid" style.

	* Quite a few code optimizations.
	* ...and there's usually more stuff in the CHANGES file.


Installation
--------------------

This feedjack fork is a regular package for Python 2.7 (not 3.X), but not in
pypi, so can be installed from a checkout with something like that:

	python setup.py install

That will install feedjack to a python site-path, so it can be used as a Django
app.

Note that to install stuff in system-wide PATH and site-packages, elevated
privileges are often required.
Use
[~/.pydistutils.cfg](http://docs.python.org/install/index.html#distutils-configuration-files)
or [virtualenv](http://pypi.python.org/pypi/virtualenv) to do unprivileged
installs into custom paths.

Better way would be to use [pip](http://pip-installer.org/) to install all the
necessary dependencies as well:

	% pip install 'git+https://github.com/mk-fg/feedjack.git#egg=feedjack'

After that you must set up your Feedjack static directory inside your Django
[STATIC_URL](http://docs.djangoproject.com/en/dev/ref/settings/#static-url)
directory.
It must be set in a way that Feedjack’s static directory can be reached at
"STATIC_URL/feedjack/".

For instance, if your STATIC_URL resolves to "/var/www/htdocs", and Feedjack was
installed in /usr/lib/python2.7/site-packages/feedjack, just type this:

	% ln -s /usr/lib/python2.7/site-packages/feedjack/static/feedjack /var/www/htdocs/feedjack

Alternatively, standard
[django.contrib.staticfiles](https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/)
app [can be used to copy/link static
files](https://docs.djangoproject.com/en/dev/howto/static-files/) with
"./manage.py collectstatic" command.

You must also add 'feedjack' in your settings.py under
[INSTALLED_APPS](http://docs.djangoproject.com/en/dev/ref/settings/#installed-apps)
and then run "[./manage.py
syncdb](http://docs.djangoproject.com/en/dev/ref/django-admin/#syncdb)" from the
command line.

Make sure to add/uncomment "django.contrib.admin" app ([Django admin
interface](https://docs.djangoproject.com/en/dev/ref/contrib/admin/)) before
runnng syncdb as well, since it's the most convenient and supported way to
configure and control feedjack.
Otherwise the next best way would be to manipulate models from the python code
directly, which might be desirable for some kind of migration or other automatic
configuration.

If [South app](http://south.aeracode.org) is available (highly recommended),
make sure to add it to INSTALLED_APPS as well, so it'd be able to apply future
database schema updates effortlessly.
Don't forget to run "./manage.py migrate feedjack" in addition to syncdb in that
case.

Then you must add an entry for feedjack.urls in your Django "urls.py" file, so
it'd look something like this (with admin interface also enabled on "/admin/"):

	urlpatterns = patterns( '',
		(r'^admin/', include('django.contrib.admin.urls')),
		(r'', include('feedjack.urls')) )

After that you might want to check out /admin section (if django.contrib.admin
app was enabled) to create a feedjack site, otherwise sample default site will
be created for you on the first request.


### Requirements

* [Python 2.7](python.org)
* [feedparser 4.1+](feedparser.org)
* [Django 1.4+](djangoproject.com)
* (optional) [lxml](http://lxml.de) - used for html mangling in some themes (fern, plain)
* (optional) [South](http://south.aeracode.org) - for automated database schema
	migrations (when updating from older Feedjack versions)


### Updating from older versions

The only non-backwards-compatible changes should be in the database schema, thus
requiring migration, but it's much easier (automatic, even) than it sounds.

Feedjack uses South for database migration, so it [has to be
installed](http://south.readthedocs.org/en/latest/installation.html) if database
schema migrations are necessary.
Don't forget to [add "south" to
INSTALLED_APPS](http://south.readthedocs.org/en/latest/installation.html#installation-configure)
afterwards.

After that, use something like this to see current database schema version and
which migrations are necessary:

	% ./manage.py migrate --list

	feedjack
	  ...
	  (*) 0013_auto__add_field_filterbase_crossref_rebuild__add_field_filterbase_cros
	  ( ) 0014_auto__add_field_post_hidden
	  ( ) 0015_auto__add_field_feed_skip_errors
	  ( ) 0016_auto__chg_field_post_title__chg_field_post_link
	  ( ) 0017_auto__chg_field_tag_name

Here you can see at which version the current schema is and how far it's behind
what code (models.py) expects it to be.

If South was just installed, you may have to specify initial schema version
manually by using command like `./manage.py migrate feedjack 0013 --fake`.
Best way to manually find which model version was used before South is probably
to inspect git history for models.py to find the first not-yet applied change to
the model classes.

All the necessary migrations can be applied with a single `./manage.py migrate feedjack`
command:

	% ./manage.py migrate feedjack

	Running migrations for feedjack:
	 - Migrating forwards to 0017_auto__chg_field_tag_name.
	 > feedjack:0014_auto__add_field_post_hidden
	 > feedjack:0015_auto__add_field_feed_skip_errors
	 > feedjack:0016_auto__chg_field_post_title__chg_field_post_link
	 > feedjack:0017_auto__chg_field_tag_name
	 - Loading initial data for feedjack.
	Installed 4 object(s) from 1 fixture(s)

In case of any issues and for more advanced usage information, please refer to
[South project documentation](http://south.readthedocs.org/en/latest/).


Configuration
--------------------

The first thing you want to do is add a Site.

To do this, open Django admin interface and create your first planet.
You must use a valid address in the URL field, since it will be used to identify
the current planet when there are multiple planets in the same instance and to
generate all the links.

Then you should add subscribers to your first planet.
A subscriber is a relation between a Feed and a Site, so when you add your first
subscriber, you must also add your first Feed by clicking in the “+” button at
the right of the Feed combobox.

Feedjack is designed to use [Django cache
system](https://docs.djangoproject.com/en/dev/topics/cache/) to store
database-intensive data like pages of posts and tagclouds, so it is highly
recomended to [configure
CACHES](http://docs.djangoproject.com/en/dev/topics/cache/#setting-up-the-cache)
in django settings (memcached, db or file).

Now that you have everything set up, run `./manage.py feedjack_update` (or
something like `DJANGO_SETTINGS_MODULE=myproject.settings feedjack_update`) to
retrieve the actual data from the feeds.
This script should be setup to be run periodically (to retreive new posts from
the feeds), which is usually a task of unix cron daemon.


Bugs, development, support
--------------------

All the issues with this fork should probably be reported to respective github
project/fork, since code here can be quite different from the original project.

Until 2012, fork was kept in [fossil](http://www.fossil-scm.org/) repo
[here](http://fraggod.net/code/fossil/feedjack/).

Original version is available at [feedjack site](http://www.feedjack.org/).


Links
--------------------

* Original feedjack project: http://www.feedjack.org/

* Other known non-github forks
	* http://git.otfbot.org/feedjack.git/
	* http://code.google.com/p/feedjack-extension/
