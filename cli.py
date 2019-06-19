from thesaurus import Thesaurus

thes = Thesaurus()

print('Type HELP to see a list of commands and instructions.\n')

while True:
    query = input('Enter a word to look it up in the thesaurus:\n')

    if query.strip() == 'HELP':
        print('QUIT'.ljust(25), 'Exits the program.')
        print('REQUIRE <word list(s)>'.ljust(25), 'Shows only results from these specific word list(s).')
        print('REQUIRE ANY').ljus(25), 'Does not show words that are not in a word list.'
        print()
        print('To add a new word list, create a txt file in the filters directory with each word on a new line. Then restart the program.')


    elif query.strip() == 'QUIT':
        quit()

    elif query.strip() == 'require any':
        thes = Thesaurus(must_match=True)

    elif len(query.strip().split()) > 1:

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