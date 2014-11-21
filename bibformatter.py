"""
Automatically reformat a .bib file and flag duplicate entries.
"""
import sys
import re
import logging
import string
import bibtexparser
import titlecase

import conferences

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

REQUIRED_KEYS = {
  "misc": ["author", "howpublished", "title", "year"],
  "inproceedings": ["author", "booktitle", "title", "year"],
  "journal": ["author", "journal", "title", "year"],
  "techreport": ["author", "howpublished", "title", "year"],
}

TITLE_ARTICLES = {
  "a": True,
  "an": True,
  "as": True,
  "on": True,
  "to": True,
  "by": True,
  "with": True,
  "from": True,
  "in": True,
  "of": True,
  "the": True,
  "and": True,
  "for": True,
  "is": True,
}

class bcolors:
  HEADER = '\033[95m'
  OKBLUE = '\033[94m'
  OKGREEN = '\033[92m'
  WARNING = '\033[93m'
  FAIL = '\033[91m'
  ENDC = '\033[0m'

def FormatCheckReference(title, author, year):
  """Create a reference from title, author, and year of the form thomas2014bib."""
  if not title or not author or not year:
    return None

  referenceTitleKey = None
  for word in title.lower().split(" "):
    if word in TITLE_ARTICLES:
      continue
    else:
      referenceTitleKey = word
      break

  firstAuthor =  author.split(" and ")[0]
  referenceAuthorKey = (firstAuthor if len(firstAuthor.split(" ")) <= 1 else
                        firstAuthor.split(" ")[-1].lower())
  reference = StripNonAZ(referenceAuthorKey) + year + StripNonAZ(referenceTitleKey)
  return reference.lower()


def FormatCheckTitle(title):
  """Format title as all capitals."""
  formattedTitle = titlecase.titlecase(re.sub("\s\+", " ", title))
  if title.strip() != formattedTitle.strip():
    logging.info("Improperly formatted title")
  return formattedTitle, False


def FormatCheckIndividualAuthor(author):
  """Format a single author as First Initial, Last Name"""
  author = author.strip()
  formatting = "space"
  if re.search(",", author):
    formatting = "comma"
    logging.info("Authors formatted as Last, First. Will reformat as First Last: %s", author)

  parts = author.split("," if formatting == "comma" else " ")

  if len(parts) <= 1:
    logging.info("Could not parse author %s. Is it a company?", author)
    return author, False
  
  firstname = parts[0].strip() if formatting == "space" else parts[1].strip()
  nameParts = parts if formatting == "space" else parts[1:] + [parts[0]]

  manualFixRequired = False
  if len(firstname) < 2 or firstname[1] == ".":
    logging.error("Abbreviated author, use full name")
    manualFixRequired = True
  return " ".join(nameParts), manualFixRequired


def FormatCheckAuthor(author):
  """Format a list of authors as first initial and last name. (K. Thomas)"""
  authorList = author.split(" and ")
  reformattedAuthorList = [FormatCheckIndividualAuthor(author) for author in authorList]
  manualFixRequired = max([result[1] for result in reformattedAuthorList])
  return re.sub("\s+", " ", " and ".join(result[0] for result in
      reformattedAuthorList)).strip(), manualFixRequired


def FormatCheckYear(year):
  """Reformat year to only digits."""
  search = re.search("(\d+)", year)
  if not search or len(search.group(1)) != 4:
    logging.error("Invalid year %s", year)  
    return year, True
  return search.group(1), False


def FormatCheckConference(conference):
  """Reformat conference titles based on a predefined list of keywords."""
  conference = StripBibtex(conference)
  bestMatch = None
  for formatter in conferences.CONFERENCE_KEYWORDS:
    keywords = formatter[0]
    title = formatter[1]
    for keyword in keywords:
      if re.search(keyword.lower(), conference.lower()):
        bestMatch = title

  if not bestMatch:
    logging.warn("Conference: Failed to parse %s", conference)
    return conference, True
  elif bestMatch != conference:
    logging.info("Reformatted conference name")

  return bestMatch, False


def FormatCheckBibType(bibtype):
  """Check whether bibtype is supported."""
  if bibtype not in ["misc", "inproceedings", "journal", "techreport"]:
    logging.info("Unsupported type: %s, defaulting to inproceedings", bibtype)
    return "inproceedings", False
  return bibtype, False


def FormatCheckEntry(entry):
  """Reformat an entire bib entry."""
  formatCheckTypes = {
    "author": FormatCheckAuthor,
    "booktitle": FormatCheckConference,
    "journal": FormatCheckConference,
    "year": FormatCheckYear,
    "type": FormatCheckBibType,
    "title": FormatCheckTitle,
  }

  newEntry = {}
  entryManualFixRequired = False

  # Process individual fields
  for key in entry:
    if key in formatCheckTypes:
      original = entry[key]
      reformatted, manualFixRequired = formatCheckTypes[key](original)
      newEntry[key] = [reformatted, manualFixRequired]

      if manualFixRequired:
        entryManualFixRequired = True

  # Entries must conform to a canonical reference ID
  if ("title" not in newEntry or "author" not in newEntry or "year" not in newEntry
      or newEntry["title"][1] or newEntry["author"][1] or newEntry["year"][1]):
    logging.warn("Could not canonicalize an ID")
    if entry["id"] == "dingledine2004tor":
      import pdb
      pdb.set_trace()

    newEntry["id"] = [entry["id"], True]
    entryManualFixRequired = True
  else:
    newEntry["id"] = [FormatCheckReference(
        newEntry["title"][0], newEntry["author"][0], newEntry["year"][0]), False]

  # Entries must conform to a minimum set of data
  for field in REQUIRED_KEYS[newEntry["type"][0]]:
    if field not in newEntry:
      logging.warn("Missing field for entry %s", field)
      newEntry[field] = ["<Missing>", True]
      entryManualFixRequired = True

  return newEntry, entryManualFixRequired


def StripBibtex(text):
  """Strip surrounding whitespace, {}, "", and trailing commas."""
  return re.sub("\"", "", re.sub("}", "", re.sub("{", "", text.split("=")[-1]))).strip().strip(",")


def StripNonAZ(text):
  """Remove all non A-Z characters."""
  return re.sub("[^A-Za-z]", "", text)


def WriteBibEntry(formattedEntry, outputFile):
  """Output bibtex to a file."""
  text = "@%s{%s,\n" % (formattedEntry["type"][0], formattedEntry["id"][0])
  for field in formattedEntry:
    value, fixRequired = formattedEntry[field]
    if field != "type" and field != "id":
      text += "  %s={%s},%s\n" % (field, value, "*" if fixRequired else "")
  text += "}\n\n"
  outputFile.write(text.encode("utf-8"))


def main():
  """Read a filename from the command line and output the valid bib entries."""
  validBibOutput = open("validBib.bib", "w")
  invalidBibOutput = open("invalidBib.bib", "w")

  duplicates = {}
  bibDatabase = bibtexparser.loads(open(sys.argv[1]).read())
  for entry in bibDatabase.entries:
    formattedEntry, entryManualFixRequired = FormatCheckEntry(entry)
    for key in formattedEntry:
      value, manualFixRequired = formattedEntry[key]
      color = bcolors.OKGREEN if not manualFixRequired else bcolors.WARNING
      print "%s%s = {%s}%s" % (color, key, value, bcolors.ENDC)
    print "-"*20

    key = formattedEntry["id"][0]
    if key in duplicates:
      continue
               
    WriteBibEntry(formattedEntry, validBibOutput if not entryManualFixRequired
        else invalidBibOutput)
    duplicates[key] = True


if __name__ == "__main__":
  main()
