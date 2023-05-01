from collections import defaultdict
import json

# SITE_PATH = '/home/cemiller220/mysite'
SITE_PATH = '/Users/cmiller/Documents/casting_app/dw_casting_backend'

DEFAULT_TYPES = defaultdict(list)
# default_keys: cast_list, change_log
DEFAULT_TYPES['metadata'] = {}
DEFAULT_TYPES['dancer_overlap'] = {}
DEFAULT_TYPES['available_next'] = {}


def get_data(args, node):
    if 'season' in args.keys() and 'city' in args.keys():
        season = args['season']
        city = args['city']
        try:
            data = json.load(open(f'{SITE_PATH}/data/{city}/season{season}/{node}.json'))
            return data
        except FileNotFoundError:
            print('file not found')
            return DEFAULT_TYPES[node]
    else:
        return DEFAULT_TYPES[node]


def save_data(data, args, node):
    season = args['season']
    city = args['city']
    json.dump(data, open(f'{SITE_PATH}/data/{city}/season{season}/{node}.json', 'w'))


def calculate_show_order_stats(show_order, dancer_overlap):
    num_back_to_back = 0
    num_one_between = 0
    num_two_between = 0
    for ind, piece in enumerate(show_order[:-1]):
        if piece != 'INTERMISSION' and piece != '':
            if show_order[ind+1] == 'INTERMISSION':
                continue
            num_back_to_back += len(dancer_overlap[piece][show_order[ind+1]])
            if ind == len(show_order) - 2:
                continue

            if show_order[ind+2] == 'INTERMISSION':
                continue
            num_one_between += len(dancer_overlap[piece][show_order[ind+2]])
            if ind == len(show_order) - 3:
                continue

            if show_order[ind+3] == 'INTERMISSION':
                continue
            num_two_between += len(dancer_overlap[piece][show_order[ind+3]])
    return {'num_back_to_back': num_back_to_back, 'num_one_between': num_one_between, 'num_two_between': num_two_between}


def get_all_cast_statuses(cast_list):
    return {piece['name']: {dancer['name']: dancer['status'] for dancer in piece['cast']} for piece in cast_list}


def get_all_dancer_statuses(choreographer_prefs, dancer_prefs, all_cast_statuses):
    all_choreographer_prefs = {piece['name']: {**{dancer: ('favorite', ind) for ind, dancer in enumerate(piece['prefs']['favorites'])},
                                               **{dancer: ('alternate', ind+len(piece['prefs']['favorites'])) for ind, dancer in enumerate(piece['prefs']['alternates'])}}
                               for piece in choreographer_prefs}

    all_dancer_statuses = {}
    for pref in dancer_prefs:
        dancer = pref['name']
        all_dancer_statuses[dancer] = {}
        for piece in pref['prefs']:
            try:
                status = all_cast_statuses[piece][dancer]
            except KeyError:
                status = ''

            try:
                preference_rank = all_choreographer_prefs[piece][dancer]
            except KeyError:
                preference_rank = ('', '')

            all_dancer_statuses[dancer][piece] = {'preference': preference_rank[0], 'status': status, 'rank': preference_rank[1]}
    return all_dancer_statuses


def get_all_dancer_validation(dancer_prefs, all_dancer_statuses, metadata):
    dancer_max_prefs = {pref['name']: {'max_dances': pref['max_dances'], 'max_days': pref['max_days']} for pref in dancer_prefs}
    all_dancer_validation = {}
    for dancer, statuses in all_dancer_statuses.items():
        pieces_cast = [piece for piece, status in statuses.items() if status['status'] == 'cast']
        num_dances_cast = len(pieces_cast)
        num_days_cast = len(set([metadata['times'][piece]['day'] for piece in pieces_cast]))

        times_cast = [metadata['times'][piece]['day'] + str(metadata['times'][piece]['time']) for piece in pieces_cast]
        any_same_time = len(set(times_cast)) != len(times_cast)

        num_dances_waitlist = len([piece for piece, status in statuses.items() if status['status'] == 'waitlist'])
        done = False
        if num_dances_waitlist == 0 and num_dances_cast <= dancer_max_prefs[dancer]['max_dances'] and num_days_cast <= dancer_max_prefs[dancer]['max_days']:
            done = True

        all_dancer_validation[dancer] = {'num_dances_cast': num_dances_cast, 'num_days_cast': num_days_cast, 'any_same_time': any_same_time, 'done': done}

    return all_dancer_validation


def drop_from_list(dancer_name, cast_list, keep_drop):
    changes = []
    for piece in cast_list:
        # loop through all pieces and check if that piece is in keep_drop and if it's set to drop, if yes...
        if piece['name'] in keep_drop.keys() and keep_drop[piece['name']] == 'drop':
            # remove dancer from that cast list
            dancer_ind = [ind for ind, dancer in enumerate(piece['cast']) if dancer['name'] == dancer_name][0]
            dancer_status = piece['cast'][dancer_ind]['status']
            del piece['cast'][dancer_ind]
            changes.insert(0, {'name': dancer_name, 'piece': piece['name'], 'type': 'drop'})

            # if the dancer was cast, add the next dancer from the waitlist
            if dancer_status == 'cast':
                try:
                    waitlist_ind = [ind for ind, dancer in enumerate(piece['cast']) if dancer['status'] == 'waitlist'][0]
                    piece['cast'][waitlist_ind]['status'] = 'cast'
                    changes.insert(0, {'name': piece['cast'][waitlist_ind]['name'], 'piece': piece['name'], 'type': 'add'})
                except IndexError:
                    # no one on waitlist
                    continue

    return cast_list, changes


def drop_all_same_times(metadata, cast_list, dancer_prefs):
    dancer_prefs_dict = {pref['name']: pref['prefs'] for pref in dancer_prefs}
    changes = []
    for time_slot, day in metadata['rehearsal_schedule'].items():
        for pieces in day.values():
            if len(pieces) > 1:
                casts = [cast for cast in cast_list if cast['name'] in pieces]
                cast_overlap = set([dancer['name'] for dancer in casts[0]['cast'] if dancer['status'] == 'cast']).intersection([dancer['name'] for dancer in casts[1]['cast'] if dancer['status'] == 'cast'])
                while len(cast_overlap) != 0:
                    for dancer_name in cast_overlap:
                        piece0_rank = dancer_prefs_dict[dancer_name].index(pieces[0])
                        piece1_rank = dancer_prefs_dict[dancer_name].index(pieces[1])

                        drop_ind = 1 if piece0_rank < piece1_rank else 0

                        dancer_ind = [ind for ind, dancer in enumerate(casts[drop_ind]['cast']) if dancer['name'] == dancer_name][0]
                        del casts[drop_ind]['cast'][dancer_ind]
                        changes.insert(0, {'name': dancer_name, 'piece': casts[drop_ind]['name'], 'type': 'drop'})
                        try:
                            waitlist_ind = [ind for ind, dancer in enumerate(casts[drop_ind]['cast']) if dancer['status'] == 'waitlist'][0]
                            casts[drop_ind]['cast'][waitlist_ind]['status'] = 'cast'
                            changes.insert(0, {'name': casts[drop_ind]['cast'][waitlist_ind]['name'], 'piece': casts[drop_ind]['name'], 'type': 'add'})
                        except IndexError:
                            continue

                    cast_overlap = set([dancer['name'] for dancer in casts[0]['cast'] if dancer['status'] == 'cast']).intersection([dancer['name'] for dancer in casts[1]['cast'] if dancer['status'] == 'cast'])

    return cast_list, changes


def calculate_dancer_overlap_available_next(cast_list):
    dancer_overlap = {}
    allowed_next = {}
    for cast1 in cast_list:
        piece1 = cast1['name']
        allowed_next[piece1] = []
        dancer_overlap[piece1] = {}
        for cast2 in cast_list:
            piece2 = cast2['name']
            if piece1 != piece2:
                dancers1 = [dancer['name'] for dancer in cast1['cast'] if dancer['status'] == 'cast']
                dancers2 = [dancer['name'] for dancer in cast2['cast'] if dancer['status'] == 'cast']
                dancer_overlap[piece1][piece2] = list(set(dancers1).intersection(dancers2))
                if len(dancer_overlap[piece1][piece2]) == 0:
                    allowed_next[piece1].append(piece2)

    return dancer_overlap, allowed_next
