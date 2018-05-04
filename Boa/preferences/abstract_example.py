# add participant
participant = Participant(
    ID = 'example',
    firstname = 'Albert',
    lastname = 'Uthor',
    title = 'Dr.',
    email = 'test@example.com',
    institute = 'My University',
    department = 'Department for Chemistry',
    street = 'Example street 1',
    postal_code = '12345',
    city = 'Hometown',
    country = 'Germany',
    contribution = 'Poster',
    paid = False,
    abstract = None,
    events = '',
    rank = 'participant',
)

# affiliations
affiliation1 = Affiliation(
    key = 1,
    institute = 'My University',
    department = 'Department for Chemistry',
    street = 'Example street 1',
    postal_code = '12345',
    city = 'Hometown',
    country = 'Germany'
)
affiliation2 = Affiliation(
    key = 2,
    institute = 'Other University',
    department = 'Department for Physical Chemistry',
    street = 'Example street 2',
    postal_code = '12345',
    city = 'Othertown',
    country = 'Austria'
)

# authors
author1 = Author(
    key = 1,
    firstname = 'Albert',
    lastname = 'Uthor',
    affiliation_keys = '21'
)
author2 = Author(
    key = 2,
    firstname = 'C.O.',
    lastname = 'Author',
    affiliation_keys = '2'
)

# abstract
abstract = Abstract(
    category ='Other',
    title = r'An example abstract',
content = '''This is just an *example* **abstract** to show you how this works.\n\nHere is a citation using footnotes [^1]. You  may also use inline footnotes ^[B. Uthor, et. all, Science, (2010), **12**, 10-15].
For chemical sum formulae you can use the `$\\ce{}$` macro: $\\ce{H3O+}$.\n
If you want to use greek letters, remember to enclose them in math mode: $\\alpha\\beta\\gamma$, $\\alpha$-amino acids.

Lorem ipsum dolor sit amet, consectetur adipiscing elit. Praesent vitae augue neque. In nec ex sit amet nulla efficitur euismod. Vivamus blandit aliquam ante. Praesent volutpat, ante ut gravida condimentum, enim ligula aliquet purus, vitae convallis diam lorem sed mi. Praesent vel ante a libero semper aliquet. Nulla sagittis purus vitae dignissim maximus. Sed tristique nunc eros, at finibus augue consequat sed. Maecenas fermentum turpis eget velit finibus mollis.

Aenean pretium augue vel turpis accumsan, et accumsan est mollis. Etiam interdum lectus sed aliquet pretium. Maecenas eu faucibus erat. Curabitur euismod eros sit amet facilisis tincidunt. Aliquam dignissim sapien id volutpat hendrerit. Maecenas mattis tempus scelerisque. Nulla condimentum lectus quis dui pharetra, id posuere lectus placerat. Etiam ut risus eu sapien euismod facilisis. Sed molestie eleifend nibh non sollicitudin. Suspendisse vel imperdiet ex, at dapibus nulla. Nam accumsan scelerisque diam, sit amet vehicula lectus pharetra vel. Suspendisse et nunc eget quam pretium porta sed sed orci.\n

[^1]: A. Uthor, et.al., Nature, (2015), **1**, 1-10''',
    img_use = True,
    img_width = 100,
    img_caption = r'Give your figure a nice caption! Hint: If possible, use vector graphics (as supported by pdf) to avoid ugly artificial edges.'
)

abstract.authors = [author1, author2]
abstract.affiliations = [affiliation1, affiliation2]
participant.abstract = abstract
