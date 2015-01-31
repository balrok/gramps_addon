== My Gramps development ==


# automatically reload addons in Gramps without restart required
# visualize a family tree


-- 1. Reload addons --

This happens in file *xyz*. TODO write commits

-- 2. Family Tree --
This is based on the *xyz* addon, which utilizes the GraphViz *todo link* library.

I tailored it to my needs, but tried to keep the implementation still a bit generic.

My goal was similar to the hourglass view.

I have one person in the center with his spouses and get all descendants and ancestors of those initial persons. When ancestor have siblings they are abbreviated in the family-bubble. When the descendants have a spouse with unrelated children, those will be abbreviated inside that person.


TODO:

* bigger images and text when enough space - currently it will increase the arch length
* more customizable which persons to use:
	maybe add person per hand and then asking in popup if parents, children
	if yes, it will further ask and in the end, all are inside
* correctly order the people by:
	family (1. child of a family)
	number in family
* show number of childs and grandchilds of people in this round view, where normally the marriage is inside

