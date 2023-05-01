import numpy as np
from itertools import combinations
import time
from collections import Counter
from tqdm import tqdm


def flatten(t):
    return [item for sublist in t for item in sublist]


def n_days_compare(cast_per_day, max_days):
    if len([day for day, n_cast in cast_per_day.items() if n_cast >= 1]) < max_days:
        return 'less'
    elif len([day for day, n_cast in cast_per_day.items() if n_cast >= 1]) == max_days:
        return 'equal'
    else:
        return 'more'


def n_dances_compare(cast_per_day, max_dances):
    if sum(cast_per_day.values()) < max_dances:
        return 'less'
    elif sum(cast_per_day.values()) == max_dances:
        return 'equal'
    else:
        return 'more'


def casting_is_valid(cast_per_day, max_days, max_dances):
    day_compare = n_days_compare(cast_per_day=cast_per_day, max_days=max_days)
    dance_compare = n_dances_compare(cast_per_day=cast_per_day, max_dances=max_dances)
    return day_compare in ['less', 'equal'] and dance_compare in ['less', 'equal']


def get_max_possible_n(day_statuses):
    return {day: sum([len(status) != 0 for status in statuses]) for day, statuses in day_statuses.items()}


def get_current_cast_per_day(day_statuses, keep_drop=None):
    if keep_drop:
        current_cast_per_day = {day: sum([len([(piece_name, piece_status, piece_rank) for piece_name, piece_status, piece_rank in status if piece_status == 'cast' and keep_drop[piece_name] == 'keep']) != 0
                                          for status in statuses]) for day, statuses in day_statuses.items()}
    else:
        current_cast_per_day = {day: sum([len([(piece_name, piece_status, piece_rank) for piece_name, piece_status, piece_rank in status if piece_status == 'cast']) != 0
                                          for status in statuses]) for day, statuses in day_statuses.items()}
    assert max(current_cast_per_day.values()) <= 3, 'Error: current_cast_per_day max > 3'
    return current_cast_per_day


def get_keep_drop(current_pref, dancer_statuses, metadata):
    # first run in finalize mode
    final_keep_drop, day_statuses = keep_drop_default(current_pref=current_pref, dancer_statuses=dancer_statuses, metadata=metadata)
    final_keep_drop = keep_drop_finalize(current_pref=current_pref, day_statuses=day_statuses, keep_drop=final_keep_drop)

    # then run in standard mode
    if current_pref['max_dances'] == 1:
        standard_keep_drop = keep_drop_max1dance(current_pref=current_pref, dancer_statuses=dancer_statuses)
    else:
        start = time.time()
        standard_keep_drop = keep_drop_loop(current_pref=current_pref, dancer_statuses=dancer_statuses, metadata=metadata)
        end = time.time()
        print(end-start)

    return {'finalize': final_keep_drop, 'standard': standard_keep_drop}


def keep_drop_default(current_pref, dancer_statuses, metadata):
    keep_drop = {piece: 'keep' for piece in current_pref['prefs'] if dancer_statuses[piece]['status'] in ['cast', 'waitlist']}

    day_statuses = {'Sunday': [[], [], []], 'Monday': [[], [], []], 'Tuesday': [[], [], []], 'Wednesday': [[], [], []], 'Thursday': [[], [], []]}
    time_slot_inds = {'first': 0, 'second': 1, 'third': 2}
    for time_slot, days in metadata['rehearsal_schedule'].items():
        for day, pieces in days.items():
            for piece in pieces:
                # build day_statuses
                status = dancer_statuses.get(piece, {}).get('status', '')
                if status == '':
                    continue
                try:
                    dancer_pref_rank = current_pref['prefs'].index(piece)
                except ValueError:
                    continue

                day_statuses[day][time_slot_inds[time_slot]].append((piece, status, dancer_pref_rank))

            # drop pieces at the same time:
            # if higher ranked piece is cast, and lower ranked piece is cast or waitlisted, drop dancer from lower ranked piece
            if len(pieces) == 2:
                try:
                    piece0_status = dancer_statuses[pieces[0]]['status']
                    piece1_status = dancer_statuses[pieces[1]]['status']
                    piece0_rank = current_pref['prefs'].index(pieces[0])
                    piece1_rank = current_pref['prefs'].index(pieces[1])
                except KeyError:
                    continue
                except ValueError:
                    continue

                if piece0_status == 'cast' and piece1_status in ['cast', 'waitlist'] and piece0_rank < piece1_rank:
                    keep_drop[pieces[1]] = 'drop'
                elif piece1_status == 'cast' and piece0_status in ['cast', 'waitlist'] and piece1_rank < piece0_rank:
                    keep_drop[pieces[0]] = 'drop'

    # TODO: figure out if this is still needed, if yes move to other function
    # max_possible_n = get_max_possible_n(day_statuses=day_statuses)
    # current_cast_per_day = get_current_cast_per_day(day_statuses=day_statuses)
    #
    # if max(current_cast_per_day.values()) != 0:
    #     # don't run this if dancer hasn't been cast in anything yet (it will error, and also unnecessary)
    #     rank_to_beat = max(sorted(flatten([[min([piece_rank for piece_name, piece_status, piece_rank in status if piece_status == 'cast'])
    #                                         for status in statuses if len([piece_rank for piece_name, piece_status, piece_rank in status if piece_status == 'cast']) != 0]
    #                                        for day, statuses in day_statuses.items()]))[:min(current_pref['max_days'], current_pref['max_dances'])])
    #
    #     # if cast in more days than max_days
    #     # drop piece if day has only 1 waitlisted (or only 2 waitlisted at same time) and it is lower ranked than the top N pieces currently cast
    #     if sum(current_cast_per_day.values()) >= current_pref['max_days']:
    #         for day in [day for day, max_n in max_possible_n.items() if max_n == 1 and current_cast_per_day[day] == 0]:
    #             for piece_name, piece_rank in flatten([[(piece_name, piece_rank) for piece_name, piece_status, piece_rank in status] for status in day_statuses[day] if len(status) > 0]):
    #                 if piece_rank > rank_to_beat:
    #                     keep_drop[piece_name] = 'drop'

    return keep_drop, day_statuses


def keep_drop_max1dance(current_pref, dancer_statuses):
    # if dancer only wants 1 dance, find top dance they've been cast in and drop everything below it
    keep_drop = {}

    cast_ranks = [current_pref['prefs'].index(piece) for piece, status in dancer_statuses.items() if status['rank'] != '' and status['status'] == 'cast']
    min_rank = min(cast_ranks) if len(cast_ranks) != 0 else 1000000
    for piece, status in dancer_statuses.items():
        if status['status'] == '':
            continue

        if current_pref['prefs'].index(piece) <= min_rank:
            keep_drop[piece] = 'keep'
        else:
            keep_drop[piece] = 'drop'

    return keep_drop


# def keep_drop_max1day(keep_drop, day_statuses):
#     # TODO: verify this works for max 1 day, 2 dances (probably some adjustments needed?)
#     max_possible_n = get_max_possible_n(day_statuses=day_statuses)
#     current_cast_per_day = get_current_cast_per_day(day_statuses=day_statuses)
#
#     current_max_n = max(current_cast_per_day.values())
#     current_max_n_days = [day for day, num_cast in current_cast_per_day.items() if num_cast == current_max_n]
#     best_current_rank = 100000
#     # for the days with the most cast current, get the best average rank
#     for day in current_max_n_days:
#         day_current_ranks = [min([piece_rank for piece_name, piece_status, piece_rank in statuses if piece_status == 'cast']) for statuses in day_statuses[day]
#                              if len([piece_rank for piece_name, piece_status, piece_rank in statuses if piece_status == 'cast']) != 0]
#         if np.mean(day_current_ranks) < best_current_rank:
#             best_current_rank = np.mean(day_current_ranks)
#
#     for day, max_n in max_possible_n.items():
#         if max_n < current_max_n:
#             # if this day has fewer possible dances than the dancer's best day currently, drop everything from this day
#             for piece_name, piece_status, piece_rank in flatten(day_statuses[day]):
#                 keep_drop[piece_name] = 'drop'
#
#         elif max_n == current_max_n:
#             # if this day has the same number of possible dances as the dancer's best day currently,
#             # check the best possible average rank with
#             day_best_ranks = [min([piece_rank for piece_name, piece_status, piece_rank in statuses]) for statuses in day_statuses[day]
#                               if len([piece_rank for piece_name, piece_status, piece_rank in statuses]) != 0]
#             if np.mean(sorted(day_best_ranks)[:current_max_n]) > best_current_rank and 0 not in day_best_ranks:
#                 for piece_name, piece_status, piece_rank in flatten(day_statuses[day]):
#                     keep_drop[piece_name] = 'drop'
#             elif 0 < current_cast_per_day[day] < current_max_n:
#                 # decide if we should drop the current cast piece(s) on this day, i.e.
#                 # if we combine the current cast piece(s) with waitlist pieces from other time slots, would we keep them? if not, set to drop
#                 all_cast_ranks = []
#                 all_cast_pieces = []
#                 waitlist_best_ranks = []
#                 for statuses in day_statuses[day]:
#                     cast_ranks = [piece_rank for piece_name, piece_status, piece_rank in statuses if piece_status == 'cast']
#                     cast_pieces = [piece_rank for piece_name, piece_status, piece_rank in statuses if piece_status == 'cast']
#                     if len(cast_ranks) > 0:
#                         all_cast_ranks.append(min(cast_ranks))
#                         all_cast_pieces.extend(cast_pieces)
#                     else:
#                         waitlist_ranks = [piece_rank for piece_name, piece_status, piece_rank in statuses if piece_status == 'waitlist']
#                         if len(waitlist_ranks) > 0:
#                             waitlist_best_ranks.append(min(waitlist_ranks))
#
#                 assert len(all_cast_ranks) + len(waitlist_best_ranks) == current_max_n, 'Error: wrong number of items'  # check assumption here
#                 ranks_to_check = all_cast_ranks + waitlist_best_ranks
#                 if np.mean(ranks_to_check) > best_current_rank and 0 not in ranks_to_check:
#                     for piece_name in all_cast_pieces:
#                         keep_drop[piece_name] = 'drop'
#
#     return keep_drop


# def keep_drop_single_cast_days(keep_drop, day_statuses, max_days):
#     # TODO: combine this with second part of default function (move it out of default, and double check max1day still works)
#     max_possible_n = get_max_possible_n(day_statuses=day_statuses)
#     current_cast_per_day = get_current_cast_per_day(day_statuses=day_statuses)
#
#     if (len([day for day, n_cast in current_cast_per_day.items() if n_cast >= 1]) > max_days and
#             len([day for day, n_cast in current_cast_per_day.items() if n_cast == 1 and max_possible_n[day] == 1]) > 0):
#         daily_best_rank = {}
#         for day, statuses in day_statuses.items():
#             day_cast_ranks = flatten([[piece_rank for piece_name, piece_status, piece_rank in status if piece_status == 'cast'] for status in statuses])
#
#             if len(day_cast_ranks) > 0:
#                 daily_best_rank[day] = min(day_cast_ranks)
#         rank_to_beat = sorted(daily_best_rank.values())[max_days-1]
#
#         for day in [day for day, n_cast in current_cast_per_day.items() if n_cast == 1 and max_possible_n[day] == 1]:
#             piece_name, piece_status, piece_rank = sorted(flatten([[(piece_name, piece_status, piece_rank)
#                                                                     for piece_name, piece_status, piece_rank in status
#                                                                     if piece_status == 'cast']
#                                                                    for status in day_statuses[day]]),
#                                                           key=lambda x: x[2])[0]
#             if piece_rank > rank_to_beat:
#                 keep_drop[piece_name] = 'drop'
#     return keep_drop


def set_all_waitlist_to_drop(keep_drop, day_statuses):
    for day, statuses in day_statuses.items():
        for piece_name, piece_status, _ in flatten(statuses):
            if piece_status == 'waitlist':
                keep_drop[piece_name] = 'drop'

    return keep_drop


def set_waitlist_on_noncast_days_to_drop(keep_drop, day_statuses, current_cast_per_day):
    for day, statuses in day_statuses.items():
        if current_cast_per_day[day] == 0:
            for piece_name, piece_status, _ in flatten(statuses):
                if piece_status == 'waitlist':
                    keep_drop[piece_name] = 'drop'

    return keep_drop


def set_all_cast_from_day_to_drop(day, day_statuses, keep_drop):
    for piece_name, piece_status, _ in flatten(day_statuses[day]):
        if piece_status == 'cast':
            keep_drop[piece_name] = 'drop'

    return keep_drop


def finalize_waitlist(current_cast_per_day, current_pref, day_statuses, keep_drop):
    if n_dances_compare(cast_per_day=current_cast_per_day, max_dances=current_pref['max_dances']) == 'equal':
        # this dancer is cast in the exact number of dances they want and number of days is good too (from previous if statement)
        # set all waitlist to drop
        keep_drop = set_all_waitlist_to_drop(keep_drop=keep_drop, day_statuses=day_statuses)
    elif n_days_compare(cast_per_day=current_cast_per_day, max_days=current_pref['max_days']) == 'equal':
        # this dancer is cast in too few dances, but they don't want any more days than what they have
        # keep any waitlist on the same day as cast, but drop any waitlist on different days
        keep_drop = set_waitlist_on_noncast_days_to_drop(keep_drop=keep_drop, day_statuses=day_statuses, current_cast_per_day=current_cast_per_day)

    # else, n_dances < max_dances and n_days < max_days
    # so dancer would be happy with more dances on an additional day
    # keep all waitlist (no changes to keep_drop)

    return keep_drop


def keep_drop_finalize(current_pref, day_statuses, keep_drop):
    # get cast_per_day using the default keep_drop (i.e. same time dropped)
    current_cast_per_day = get_current_cast_per_day(day_statuses=day_statuses, keep_drop=keep_drop)
    if max(current_cast_per_day.values()) == 0:
        return keep_drop

    # first get all cast dances to be valid based on prefs
    if not casting_is_valid(cast_per_day=current_cast_per_day, max_days=current_pref['max_days'], max_dances=current_pref['max_dances']):
        # this dancer is cast in too many dances or on too many days
        # figure out which cast to drop
        if n_dances_compare(cast_per_day=current_cast_per_day, max_dances=current_pref['max_dances']) in ['equal', 'less']:
            # number of dances is valid, so problem must be too many days
            # keep the top N days based on # of dances cast and average rank of cast dances
            daily_cast_keep_ranks = {day: [piece_rank for piece_name, piece_status, piece_rank in flatten(statuses)
                                           if piece_status == 'cast' and keep_drop[piece_name] == 'keep']
                                     for day, statuses in day_statuses.items()}
            top_n_days = sorted(current_cast_per_day,
                                key=lambda x: (-1*current_cast_per_day.get(x), np.mean(daily_cast_keep_ranks.get(x)), min(daily_cast_keep_ranks.get(x), default=1000)))[:current_pref['max_days']]
            for day in [day for day, n_cast in current_cast_per_day.items() if n_cast != 0]:
                if day not in top_n_days:
                    keep_drop = set_all_cast_from_day_to_drop(day=day, day_statuses=day_statuses, keep_drop=keep_drop)

        elif n_days_compare(cast_per_day=current_cast_per_day, max_days=current_pref['max_days']) in ['equal', 'less']:
            # number of days is valid, so problem must be too many dances
            # keep top N dances based on rank
            sorted_cast_ranks = sorted(flatten([[piece_rank for piece_name, piece_status, piece_rank in flatten(statuses)
                                                 if piece_status == 'cast' and keep_drop[piece_name] == 'keep']
                                                for day, statuses in day_statuses.items()]))
            for rank in sorted_cast_ranks[current_pref['max_dances']:]:
                keep_drop[current_pref['prefs'][rank]] = 'drop'
        else:
            # both are too large
            # get all combinations of days (nCr), n = days with something cast, r = max days
            # get average rank of top N cast dances from those days
            # determine which combination of days has top ave rank and keep only thoses dances
            daily_cast_keep_ranks = {day: [piece_rank for piece_name, piece_status, piece_rank in flatten(statuses)
                                           if piece_status == 'cast' and keep_drop[piece_name] == 'keep']
                                     for day, statuses in day_statuses.items()}
            daily_cast_keep_ranks = {day: ranks for day, ranks in daily_cast_keep_ranks.items() if len(ranks) != 0}

            possible_ranks = {}
            for n in range(1, current_pref['max_days'] + 1):
                for days in combinations(daily_cast_keep_ranks.keys(), n):
                    possible_ranks[days] = sorted(flatten([daily_cast_keep_ranks[day] for day in days]))

            best_days = max(possible_ranks, key=lambda key: (
                min(len(possible_ranks[key]), current_pref['max_dances']),
                -1*len(key),
                -1*np.mean(possible_ranks[key][:current_pref['max_dances']]),
                -1*min(possible_ranks[key][:current_pref['max_dances']], default=1000)
            ))

            for day, n_cast in current_cast_per_day.items():
                if n_cast >= 1 and day not in best_days:
                    # drop all cast for this day
                    keep_drop = set_all_cast_from_day_to_drop(day=day, day_statuses=day_statuses, keep_drop=keep_drop)
                elif n_cast >= 1:
                    # keep top N from this day
                    for rank in possible_ranks[best_days][current_pref['max_dances']:]:
                        keep_drop[current_pref['prefs'][rank]] = 'drop'

    # now that this dancer is cast in the max or fewer # of dances and the max or fewer # of days
    # figure out keep drop of waitlist if they stay on waitlist
    new_cast_per_day = get_current_cast_per_day(day_statuses=day_statuses, keep_drop=keep_drop)
    assert casting_is_valid(cast_per_day=new_cast_per_day, max_days=current_pref['max_days'], max_dances=current_pref['max_dances']), 'Casting is Not Valid!'
    keep_drop = finalize_waitlist(current_cast_per_day=new_cast_per_day, current_pref=current_pref, day_statuses=day_statuses, keep_drop=keep_drop)

    return keep_drop


def keep_drop_loop(current_pref, dancer_statuses, metadata):
    # first check if we cast them in everything, what are the dances we keep
    # if those are all dances they're cast in, stop there and return that keep drop
    temp_dancer_statuses = {piece: {key: 'cast' if key == 'status' and value != '' else value for key, value in status.items()} for piece, status in dancer_statuses.items()}
    keep_drop, day_statuses = keep_drop_default(current_pref=current_pref, dancer_statuses=temp_dancer_statuses, metadata=metadata)
    keep_drop = keep_drop_finalize(current_pref=current_pref, day_statuses=day_statuses, keep_drop=keep_drop)

    if set([dancer_statuses[piece]['status'] for piece, action in keep_drop.items() if action == 'keep']) == {'cast'} or set(keep_drop.values()) == {'keep'}:
        # print('cast in best option')
        return keep_drop

    # otherwise this keep_drop is starting point
    final_keep_drop = keep_drop
    # {piece: 'drop' for piece in current_pref['prefs'] if dancer_statuses[piece]['status'] in ['cast', 'waitlist']}

    # check current casting first
    current_keep_drop, day_statuses = keep_drop_default(current_pref=current_pref, dancer_statuses=dancer_statuses, metadata=metadata)
    current_keep_drop = keep_drop_finalize(current_pref=current_pref, day_statuses=day_statuses, keep_drop=current_keep_drop)

    for piece, action in current_keep_drop.items():
        if action == 'keep':
            final_keep_drop[piece] = 'keep'

    if set(final_keep_drop.values()) == {'keep'}:
        # print('current casting is all keeps')
        return final_keep_drop

    # loop through adding pieces off the waitlist
    # stop if everything becomes keep
    waitlist_dancer_statuses = {piece: status for piece, status in dancer_statuses.items() if status['status'] == 'waitlist'}
    if len(waitlist_dancer_statuses.keys())-1 < 15:
        count = 0
        for n in range(1, len(waitlist_dancer_statuses.keys()))[::-1]:
            for pieces in combinations(waitlist_dancer_statuses.keys(), n):
                count += 1
                temp_dancer_statuses = {piece: {key: value for key, value in status.items()} for piece, status in dancer_statuses.items()}
                for piece in pieces:
                    temp_dancer_statuses[piece]['status'] = 'cast'

                keep_drop, day_statuses = keep_drop_default(current_pref=current_pref, dancer_statuses=temp_dancer_statuses, metadata=metadata)
                keep_drop = keep_drop_finalize(current_pref=current_pref, day_statuses=day_statuses, keep_drop=keep_drop)

                for piece, action in keep_drop.items():
                    if action == 'keep':
                        final_keep_drop[piece] = 'keep'

                if set(final_keep_drop.values()) == {'keep'}:
                    # print('all keeps')
                    return final_keep_drop

        # print(f'finished looping ({count} loops), returning result')
        return final_keep_drop
    else:
        # return default keep_drop of current casting
        # print('didnt loop, returning current')
        return current_keep_drop


def get_next_dancer_name(current_dancer_order, change_direction, all_keep_drop, mode, current_index=None):
    # TODO: new sorting:
    #  Sort by n_drop for the method (as saved in all_keep_drop)
    #  Resort every time and always take the top dancer, even if already in the list.
    #  It should never be the same dancer because n_drop gets set to 0 after a save until something changes with that dancer
    #  Maybe also save an index in the data for refreshes and to solve the problem of when a dancer shows up multiple times in the list
    if change_direction == 'next':
        if current_index and current_index < len(current_dancer_order) - 1:
            new_index = current_index + 1
            next_dancer = current_dancer_order[new_index]
        else:
            new_index = len(current_dancer_order)
            next_dancer = find_next_dancer_for_casting(all_keep_drop=all_keep_drop, mode=mode)

    elif change_direction == 'previous':
        new_index = max(current_index-1, 0)
        next_dancer = current_dancer_order[new_index]
    else:
        raise ValueError('Need to set change_direction to "next" or "previous" ')

    # if change_direction == 'next':
    #     # if we're currently on a dancer, check if they're already in the list
    #     if current_name and current_name in current_dancer_order:
    #         # if they're in the list, find their index, if it's the last index, call function to find out who's next, otherwise grab next person from saved list
    #         current_dancer_index = current_dancer_order.index(current_name)
    #         if current_dancer_index == len(current_dancer_order) - 1:
    #             next_dancer = find_next_dancer_for_casting(current_dancer_order=current_dancer_order, all_dancer_statuses=all_dancer_statuses)
    #         else:
    #             next_dancer = current_dancer_order[current_dancer_index+1]
    #     else:
    #         # if they're not in the list or no current name, just find the next person in the function
    #         next_dancer = find_next_dancer_for_casting(current_dancer_order=current_dancer_order, all_dancer_statuses=all_dancer_statuses)
    # elif change_direction == 'previous':
    #     # if we're currently on a dancer, check if they're already in the list
    #     if current_name and current_name in current_dancer_order:
    #         # if they're in the list, find their index, if they're first in the list just return the same name, otherwise take the dancer before this one
    #         current_dancer_index = current_dancer_order.index(current_name)
    #         if current_dancer_index == 0:
    #             next_dancer = current_name
    #         else:
    #             next_dancer = current_dancer_order[current_dancer_index-1]
    #     else:
    #         # if they're not in the list, take the last dancer in the list
    #         next_dancer = current_dancer_order[-1]
    # else:
    #     raise ValueError('Need to set change_direction to "next" or "previous" ')

    return next_dancer, new_index


# def sort_dancers_for_casting(all_keep_drop, mode):
    # n_cast_waitlist = {dancer: {'n_cast': len([piece for piece, status in dancer_statuses.items() if status['status'] == 'cast']),
    #                             'n_waitlist': len([piece for piece, status in dancer_statuses.items() if status['status'] == 'waitlist'])} for dancer, dancer_statuses in all_dancer_statuses.items()}
    # return sorted(n_cast_waitlist, key=lambda key: (-1*n_cast_waitlist[key]['n_cast'], -1*n_cast_waitlist[key]['n_waitlist']))


def find_next_dancer_for_casting(all_keep_drop, mode):
    # TODO: add sort key for number of cast vs waitlist drops
    n_drop_per_dancer = {dancer_name: keep_drop_details[mode]['n_drop'] for dancer_name, keep_drop_details in all_keep_drop.items()}
    return sorted(n_drop_per_dancer, key=lambda key: -1*n_drop_per_dancer[key])[0]
    # next_dancer_order = sort_dancers_for_casting(all_dancer_statuses=all_dancer_statuses)
    # dancer_run_counts = Counter(current_dancer_order)
    # ind = 0
    # next_dancer = next_dancer_order[ind]
    # while next_dancer in current_dancer_order and dancer_run_counts[next_dancer] == max(dancer_run_counts.values()):
    #     ind += 1
    #     if ind >= len(next_dancer_order):
    #         next_dancer = next_dancer_order[0]
    #         break
    #     next_dancer = next_dancer_order[ind]
    #
    # return next_dancer


def get_dancer_casting_info(dancer_name, dancer_prefs, all_dancer_statuses, all_keep_drop, mode):
    current_index = [pref['name'] for pref in dancer_prefs].index(dancer_name)
    current_pref = dancer_prefs[current_index]
    current_statuses = all_dancer_statuses[dancer_name]

    # keep_drop = get_keep_drop(current_pref=current_pref, dancer_statuses=current_statuses, metadata=metadata)
    keep_drop = all_keep_drop[dancer_name][mode]['keep_drop']
    return keep_drop, current_pref, current_statuses


def get_all_keep_drop(dancer_prefs, all_dancer_statuses, metadata):
    all_keep_drop = {}
    for dancer_name, current_statuses in tqdm(all_dancer_statuses.items()):
        current_pref = [pref for pref in dancer_prefs if pref['name'] == dancer_name][0]
        # always run in standard mode
        keep_drop = get_keep_drop(current_pref=current_pref, dancer_statuses=current_statuses, metadata=metadata)
        all_keep_drop[dancer_name] = {mode: {'keep_drop': keep_drop[mode],
                                             'n_drop': len([action for piece, action in keep_drop[mode].items() if action == 'drop'])}
                                      for mode in ['standard', 'finalize']}

    return all_keep_drop


# TODO: check implementation of finalize
#  not suggesting min days?


# TODO: implement loop version where we only look at 1 per timeslot
#  do this by checking the lower ranked piece first, if keep then also keep higher ranked piece, if drop need to check higher ranked piece...??
#  worst case here is still bad...

# TODO: implement ordering to dancers
#  do this by sorting dancers (tbd sorting criteria) and store sorted list, then each time we send back a dancer's prefs remove that name from the list
#  if list is empty or doesn't exist, re-sort the dancers and start again
#  figure out front end details, store sorting on front end? different sorting for casting vs prefs page
#  **Maybe instead of sorting on backend, sort on front end and only store current list on backend to send back to frontend on refreshes
