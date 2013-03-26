#!/usr/bin/env python
# -*- coding: utf-8 -*-
__name    = "Bullshit filter"
__version = "1.0.0"
__date    = "26.03.2013"
__author  = "Bystroushaak"
__email   = "bystrousak@kitakitsune.org"
# 
# Interpreter version: python 2.7
# This work is licensed under a Creative Commons 3.0 
# Unported License (http://creativecommons.org/licenses/by/3.0/).
# Created in Sublime text 2 editor.
#
#= Imports =====================================================================
import sys

try:
	import dhtmlparser as d
except ImportError:
	writeln("\nThis script require dhtmlparser.", sys.stderr)
	writeln("> https://github.com/Bystroushaak/pyDHTMLParser <\n", sys.stderr)
	sys.exit(1)


#= Variables ===================================================================
HTML_TEMPLATE = """<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">
<HTML>
<head>
	<title>{title}</title>
	
	<meta http-equiv="Content-Type" content="text/html; charset={charset}">
</head>

<body>

{content}

</body>
</HTML>"""



#= Functions & objects =========================================================
def __checkParamType(s):
	"Used in few other functions. Just check, if |s| is string or instance of HTMLElement."
	# check type of |s|
	dom = None
	if type(s) == str:
		dom = d.parseString(s)
	elif isinstance(s, d.HTMLElement):
		dom = s
	else:
		raise ValueError("Parameter s must be string or instance of HTMLElement!")

	return dom


def evaluateContainers(s, tags = ["p"], maxs = 3):
	"""
	Count which element in given string/HTMLElement |s| contains most of |tags|
	in depth = 1. Return |maxs| of those elements as 
	[(count, element0), (count, element1), ... , (count, element|maxs|)].

	|s| must be string or HTMLElement.
	"""

	def __countChilds(childs, tags):
		"Just count how much of |childs| is in |tags|."
		cnt = 0
		for child in childs:
			if child.getTagName().lower() in tags:
				cnt += 1

		return cnt
	#---

	tags = map(lambda x: x.lower(), tags)

	# check type of |s|
	dom = __checkParamType(s)

	# filter noise (headers and so on)
	body = dom.find("body")
	if len(body) > 0:
		dom = body[0]

	# filter tags with childs
	pparents = dom.find("", fn = lambda x: len(x.childs) > 0)

	parents = []
	for parent in pparents:
		parents.append((__countChilds(parent.childs, tags), parent))

	parents.sort(reverse = True)

	return parents[:maxs] if len(parents) > maxs else parents


def makeDoubleLinked(dom, parent = None):
	"Standard output from dhtmlparser is single-linked tree. This will make it double-linked."
	dom.parent = parent

	if len(dom.childs) > 0:
		for child in dom.childs:
			child.parent = dom
			makeDoubleLinked(child, dom)

def getPredecessors(element):
	"""
	Return list of |element|s predecesors. 
	Elements must be double linked! This means, that you have to call makeDoubleLinked(dom)
	on whole DOM before you call this function!
	"""
	if element.parent != None:
		return getPredecessors(element.parent) + [element]
	else:
		return [element]

def findCommonRoot(elements):
	"Return last common predecessor of all elements or None if not found."

	if type(elements) != list:
		raise ValueError("type of |elements| have to be list!")
	if len(elements) == 0:
		raise ValueError("|elements| is blank!")
	if len(elements) == 1:
		return elements[0]

	# convert from list of elements to lists of full paths of predecesors
	element_arr = []
	for element in elements:
		element_arr.append(getPredecessors(element))

	last_common = None
	min_len = min(map(lambda x: len(x), element_arr)) # find minimal length

	# go thru predecesors and compare them
	for i in range(min_len):
		old = None
		for elements in element_arr: # iterate thru all arrays
			if old == None:
				old = elements[i]
				continue

			if old != elements[i]:
				return last_common

			old = elements[i]
		last_common = old

	return last_common


def findLargestTextBlock(s, blocknum = 2):
	"""
	Find |blocknum| of lagest continuous text blocks and return their common 
	root (element which encapsulates all of them).
	"""
	# check type of |s|
	dom = __checkParamType(s)

	makeDoubleLinked(dom)

	# filter noise (headers and so on)
	body = dom.find("body")
	if len(body) > 0:
		dom = body[0]

	# find all text blocks
	textblocks = dom.find("", fn = lambda x: not x.isTag() and not x.isComment() and len(x.childs) <= 0)

	# count how big text block are and store it as (len, block) om eval_text_blks
	eval_text_blks = []
	for block in textblocks:
		eval_text_blks.append((len(str(block)), block))

	eval_text_blks.sort(reverse = True)

	# pick |blocknum| from evaluated and sorted blocks - |blocknum| biggest blocks
	blocks = eval_text_blks[:blocknum] if len(eval_text_blks) > blocknum else eval_text_blks
	blocks = map(lambda x: x[1], blocks) # drop blocksizes

	root = findCommonRoot(blocks)

	return str(root.getContent())


def filterBullshit(s):
	"""
	Filter bullshit from webpages.

	This function is designed to strip unwanted content from articles on web. Basically, it just
	takes largest text blocks and strip everything other (ads, menu, information bars and other bullshit).
	"""
	dom = d.parseString(s)

	# parse title (only from <head>)
	title = dom.find("head")
	if len(title) > 0:
		title = title[0].find("title")
		if len(title) > 0:
			title = title[0].getContent()
		else:
			title = ""
	else:
		title = ""

	# parse charset
	charset = ""
	charset_tag = dom.find("meta", {"http-equiv":"Content-Type"})
	if len(charset_tag) >= 1:
		for meta in charset_tag:
			if meta.params["content"].startswith("text/html; charset="):
				charset = meta.params["content"].split("=")[1]
				break
		if charset == "":
			charset = "utf-8"

	# evaluate which containers contains most of <p> tags
	containers = evaluateContainers(dom)

	content = ""
	if len(containers) > 1 and containers[0][0] == containers[-1][0]: # next line :)
		# if all containers contains same amount of <p> tags, try to find largest text block
		content = findLargestTextBlock(dom)
	else:
		content = str(containers[0][1]) # take container which contains most of <p> blocks

	# apply html template
	content = HTML_TEMPLATE                    \
				.replace("{title}", title)     \
				.replace("{charset}", charset) \
				.replace("{content}", content)

	return content



#= Unittests ===================================================================
if __name__ == '__main__':
	infected = """
	<HTML>
	<head>
		<title>This is just unittest.</title>

		<script>sneaky.javascript();</script>
		<meta http-equiv="Content-Type" content="text/html; charset=ascii">
	</head>

	<body>
		<div id="logo">¯\(°_o)/¯</div>
		<div id="menu">
			Menu:
				- <a href="herp.html">Herpington</a>
				- <a href="derp.html">Derpington</a>
		</div>

		<div id="content">
			<h1>Article, you want to read.</h1>
				Herp de derp, derp derp, da derpa derpa. Da derpa herp de durrrrrrr derpa daaa derrrr. 
				Derp derp, haha derp durrrr. De derp? Durpa Hurp da durpa durpa derrrr. De durpa herp de 
				derp derp durrr.<br>

				De derp? Durpa Hurp da durpa durpa derrrr. De durpa herp de derp derp durrr.Herp de derp, 
				derp derp, da derpa derpa. Da derpa herp de durrrrrrr derpa daaa derrrr. Derp derp, haha 
				derp durrrr.
		</div>

		<div id="wild_ads">Eat me, your cock will grow to the sky!</div>
		<div id="footer">© Herpington van Derp</div>
	</body>
	</HTML>
	"""
	
	cleaned = filterBullshit(infected)

	assert(infected != cleaned)
	assert(len(infected) > len(cleaned))
	assert("menu"     not in cleaned)
	assert("wild_ads" not in cleaned)
	assert("footer"   not in cleaned)