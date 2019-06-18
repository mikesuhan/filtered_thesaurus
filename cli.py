from thesaurus import Thesaurus

thes = Thesaurus()

while True:
    query = input('Enter a word to look it up in the thesaurus:\n')

    if len(query.strip().split()) > 1:

        # change required word list(s)
        if query.lower().startswith('require'):
            require = [item.strip() for item in query.split()[1:]]
            thes = Thesaurus(required=require)
            print('\nOnly matches in the following list{} will be shown:\n{}\n'.format(
                's' if len(require) > 1 else '',
                '\n'.join(require)
            ))
    else:
        results = thes.get_as_string(query.strip().lower())
        print()
        print(results, '\n')