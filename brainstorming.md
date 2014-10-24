 - there are no time-critical events; bank transactions are time-critical on the order of weeks; webcomics are not critical at all, ...
 - the only constraint is that the system should prevent the user from wasting their time by manually checking; delays of several hours are assumed to be acceptable.
  - there's no need for notifications that are immediately noticed (e.g. via urgent flag, pop-up)
  - not distracting the user from what they're currently doing is the top priority
  - use end-of-day digests, maybe as HTML/markdown, sent via mail, by a cronjob
 - all events can clearly be categorized: high-priority (e.g. bank transactions, MUST NOT be missed), and low-priority (e.g. newsfeeds)
  - provide two separate digests?
  - put high-prio events directly into mail, while low-prio events are listed only in the linked HTML file
 - mixing events from different sources will decrease readability
  - group events by source
 - event polling frequencies higher than the event notification frequency don't make sense
  - do event polling in the cronjob, too
  - additional benefit: error reports appear only once per digest

event sources
-------------

 - dkb-visa-parser
 - HBCI
 - RSS feeds
 - birthdays (e.g. from thunderbird address book)
 - deadlines (e.g. from sftdeadlined (TBI)) (e.g. certificate expiriation)

notification methods
--------------------

 - email (pgp-encrypted)
 - libnotify
 - XMPP

implementation
--------------

ensure that no events get lost when the program crashes (e.g. during sending of the E-Mail/generating digest HTML)
