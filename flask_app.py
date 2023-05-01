from flask import Flask, jsonify, request, redirect, url_for
from flask_cors import CORS
from data_prep_functions import *
from casting_functions import *

app = Flask(__name__)
CORS(app)


@app.route('/api/<node>', methods=['GET', 'PUT'])
def api(node):
    if request.method == 'GET':
        data = get_data(args=request.args, node=node)
        return jsonify(data)
    elif request.method == 'PUT':
        save_data(data=json.loads(request.data), args=request.args, node=node)
        return '', 204


@app.route('/config', methods=['GET', 'PUT'])
def config():
    if request.method == 'GET':
        data = json.load(open(f'{SITE_PATH}/config/current_config.json'))
        return jsonify(data)
    elif request.method == 'PUT':
        json.dump(json.loads(request.data), open(f'{SITE_PATH}/config/current_config.json', 'w'))
        return '', 204


# SHOW ORDER #

@app.route('/calculation/show_order', methods=['GET'])
def show_order_calculation():
    # TODO: add update times and load from file if possible
    cast_list = get_data(args=request.args, node='cast_list')
    dancer_overlap, allowed_next = calculate_dancer_overlap_available_next(cast_list=cast_list)

    save_data(data=dancer_overlap, args=request.args, node='dancer_overlap')
    save_data(data=allowed_next, args=request.args, node='allowed_next')

    all_show_orders = get_data(args=request.args, node='all_show_orders')
    for show_order in all_show_orders:
        stats = calculate_show_order_stats(show_order=show_order['show_order'], dancer_overlap=dancer_overlap)
        show_order['stats'] = stats

    save_data(data=all_show_orders, args=request.args, node='all_show_orders')

    return jsonify({'dancer_overlap': dancer_overlap, 'allowed_next': allowed_next, 'all_show_orders': all_show_orders})


@app.route('/calculation/save_new_show_order', methods=['PUT'])
def save_new_show_order_calculation():
    show_order = json.loads(request.data)['show_order']
    dancer_overlap = get_data(args=request.args, node='dancer_overlap')
    stats = calculate_show_order_stats(show_order=show_order, dancer_overlap=dancer_overlap)

    all_show_orders = get_data(args=request.args, node='all_show_orders')
    all_show_orders.append({'show_order': show_order, 'stats': stats})
    save_data(data=all_show_orders, args=request.args, node='all_show_orders')

    return jsonify({'all_show_orders': all_show_orders})


@app.route('/calculation/reset_show_order', methods=['GET'])
def reset_show_order_calculation():
    show_order = get_data(args=request.args, node='real_show_order')
    if len(show_order) > 0:
        dancer_overlap = get_data(args=request.args, node='dancer_overlap')
        stats = calculate_show_order_stats(show_order=show_order, dancer_overlap=dancer_overlap)

        all_show_orders = [{'show_order': show_order, 'stats': stats}]
    else:
        all_show_orders = []
    save_data(data=all_show_orders, args=request.args, node='all_show_orders')

    return jsonify({'all_show_orders': all_show_orders})


@app.route('/calculation/delete_show_order', methods=['PUT'])
def delete_show_order_calculation():
    show_order_index = json.loads(request.data)['show_order_index']
    all_show_orders = get_data(args=request.args, node='all_show_orders')
    del all_show_orders[show_order_index]
    save_data(data=all_show_orders, args=request.args, node='all_show_orders')

    return jsonify({'all_show_orders': all_show_orders})


# PREFS #
@app.route('/calculation/prefs', methods=['GET'])
def prefs_calculation():
    cast_list = get_data(args=request.args, node='cast_list')
    dancer_prefs = get_data(args=request.args, node='dancer_prefs')
    choreographer_prefs = get_data(args=request.args, node='choreographer_prefs')

    #TODO: handle request with no args
    path = request.args['path']
    print(path)
    if path == 'choreographer':
        all_cast_statuses = get_all_cast_statuses(cast_list=cast_list)
        return jsonify({'cast_list': cast_list, 'dancer_prefs': dancer_prefs,
                        'choreographer_prefs': choreographer_prefs, 'all_cast_statuses': all_cast_statuses})

    elif path == 'dancer':
        all_cast_statuses = get_all_cast_statuses(cast_list=cast_list)
        all_dancer_statuses = get_all_dancer_statuses(choreographer_prefs=choreographer_prefs, dancer_prefs=dancer_prefs, all_cast_statuses=all_cast_statuses)
        # save_data(data=all_dancer_statuses, args=request.args, node='all_dancer_statuses')
        return jsonify({'cast_list': cast_list, 'dancer_prefs': dancer_prefs,
                        'choreographer_prefs': choreographer_prefs, 'all_dancer_statuses': all_dancer_statuses})
    else:
        raise ValueError('Invalid path')


# @app.route('/calculation/run_casting', methods=['GET'])
# def run_casting_calculation():
#     cast_list = get_data(args=request.args, node='cast_list')
#     dancer_prefs = get_data(args=request.args, node='dancer_prefs')
#     choreographer_prefs = get_data(args=request.args, node='choreographer_prefs')
#
#     all_cast_statuses = get_all_cast_statuses(cast_list=cast_list)
#     all_dancer_statuses = get_all_dancer_statuses(choreographer_prefs=choreographer_prefs, dancer_prefs=dancer_prefs, all_cast_statuses=all_cast_statuses)
#     # save_data(data=all_dancer_statuses, args=request.args, node='all_dancer_statuses')
#
#     metadata = get_data(args=request.args, node='metadata')
#     all_dancer_validation = get_all_dancer_validation(dancer_prefs=dancer_prefs, all_dancer_statuses=all_dancer_statuses, metadata=metadata)
#     # save_data(data=all_dancer_validation, args=request.args, node='all_dancer_validation')
#
#     current_dancer_order = get_data(args=request.args, node='dancer_order')
#     next_dancer = get_next_dancer_for_casting(current_dancer_order=current_dancer_order, all_dancer_statuses=all_dancer_statuses)
#
#     keep_drop, current_pref, current_statuses = get_dancer_casting_info(dancer_name=next_dancer, dancer_prefs=dancer_prefs,
#                                                                         all_dancer_statuses=all_dancer_statuses, metadata=metadata,
#                                                                         mode=request.args['mode'])
#
#     changes = json.loads(request.args['changes']) if 'changes' in request.args.keys() else []
#
#     return jsonify({'cast_list': cast_list, 'dancer_prefs': dancer_prefs,
#                     'choreographer_prefs': choreographer_prefs, 'all_dancer_statuses': all_dancer_statuses,
#                     'all_dancer_validation': all_dancer_validation,
#                     'current_pref': current_pref, 'current_statuses': current_statuses,
#                     'keep_drop': keep_drop, 'changes': changes})


@app.route('/calculation/start_casting', methods=['GET'])
def start_casting_calculation():
    dancer_prefs = get_data(args=request.args, node='dancer_prefs')
    choreographer_prefs = get_data(args=request.args, node='choreographer_prefs')

    dancer_prefs_dict = {pref['name']: pref['prefs'] for pref in dancer_prefs}
    starting_cast_list = []
    for pref in choreographer_prefs:
        piece_cast = []
        extra_cast = 0
        for dancer in pref['prefs']['favorites']:
            if pref['name'] in dancer_prefs_dict[dancer]:
                piece_cast.append({'name': dancer, 'status': 'cast'})
            else:
                extra_cast += 1

        for dancer in pref['prefs']['alternates']:
            if pref['name'] in dancer_prefs_dict[dancer]:
                if extra_cast > 0:
                    piece_cast.append({'name': dancer, 'status': 'cast'})
                    extra_cast -= 1
                else:
                    piece_cast.append({'name': dancer, 'status': 'waitlist'})

        starting_cast_list.append({'name': pref['name'], 'cast': piece_cast})

    save_data(data=starting_cast_list, args=request.args, node='cast_list')
    # clear any saved progress data from previous runs
    save_data(data=[], args=request.args, node='run_casting_dancer_order')
    save_data(data=[], args=request.args, node='run_casting_changes')

    metadata = get_data(args=request.args, node='metadata')
    all_cast_statuses = get_all_cast_statuses(cast_list=starting_cast_list)
    all_dancer_statuses = get_all_dancer_statuses(choreographer_prefs=choreographer_prefs, dancer_prefs=dancer_prefs, all_cast_statuses=all_cast_statuses)
    all_keep_drop = get_all_keep_drop(dancer_prefs=dancer_prefs, all_dancer_statuses=all_dancer_statuses, metadata=metadata)
    save_data(data=all_keep_drop, args=request.args, node='all_keep_drop')

    return redirect(url_for('keep_drop_calculation', city=request.args['city'], season=request.args['season'], change_direction='next', mode=request.args['mode']))


@app.route('/calculation/keep_drop', methods=['GET', 'PUT'])
def keep_drop_calculation():
    # TODO: figure out how to handle index??
    cast_list = get_data(args=request.args, node='cast_list')
    dancer_prefs = get_data(args=request.args, node='dancer_prefs')
    choreographer_prefs = get_data(args=request.args, node='choreographer_prefs')
    # metadata = get_data(args=request.args, node='metadata')

    all_cast_statuses = get_all_cast_statuses(cast_list=cast_list)
    all_dancer_statuses = get_all_dancer_statuses(choreographer_prefs=choreographer_prefs, dancer_prefs=dancer_prefs, all_cast_statuses=all_cast_statuses)
    all_keep_drop = get_data(args=request.args, node='all_keep_drop')

    current_dancer_order = get_data(args=request.args, node='run_casting_dancer_order')
    if 'dancer_name' in request.args.keys():
        next_dancer = request.args['dancer_name']
        new_index = len(current_dancer_order)
    else:
        next_dancer, new_index = get_next_dancer_name(current_dancer_order=current_dancer_order, change_direction=request.args['change_direction'],
                                                      all_keep_drop=all_keep_drop, mode=request.args['mode'], current_index=request.args.get('current_index', None))

    keep_drop, current_pref, current_statuses = get_dancer_casting_info(dancer_name=next_dancer, dancer_prefs=dancer_prefs,
                                                                        all_dancer_statuses=all_dancer_statuses, all_keep_drop=all_keep_drop,
                                                                        mode=request.args['mode'])
    changes = get_data(args=request.args, node='run_casting_changes')

    return jsonify({'keep_drop': keep_drop, 'current_pref': current_pref, 'current_statuses': current_statuses, 'changes': changes})


@app.route('/calculation/save_pref_changes', methods=['PUT'])
def save_pref_changes_calculation():
    current_name = request.args['dancer_name']
    keep_drop = json.loads(request.data)['keep_drop']

    # drop dancer from pieces and add next dancer where needed
    cast_list = get_data(args=request.args, node='cast_list')
    cast_list, new_changes = drop_from_list(dancer_name=current_name, cast_list=cast_list, keep_drop=keep_drop)
    save_data(data=cast_list, args=request.args, node='cast_list')

    # append changes to beginning of change list
    changes = get_data(args=request.args, node='run_casting_changes')
    changes = new_changes + changes
    save_data(data=changes, args=request.args, node='run_casting_changes')

    # save this dancer in the dancer order
    current_dancer_order = get_data(args=request.args, node='run_casting_dancer_order')
    current_dancer_order.append(current_name)
    save_data(data=current_dancer_order, args=request.args, node='run_casting_dancer_order')

    # update keep drop for all dancers that had changes
    # current dancer --> set keep drop to all the keeps from the request.data
    # dancers added --> rerun the keep drop to get new changes
    all_keep_drop = get_data(args=request.args, node='all_keep_drop')

    dancer_prefs = get_data(args=request.args, node='dancer_prefs')
    choreographer_prefs = get_data(args=request.args, node='choreographer_prefs')
    all_cast_statuses = get_all_cast_statuses(cast_list=cast_list)
    all_dancer_statuses = get_all_dancer_statuses(choreographer_prefs=choreographer_prefs, dancer_prefs=dancer_prefs, all_cast_statuses=all_cast_statuses)
    metadata = get_data(args=request.args, node='metadata')
    for dancer_name in set([change['name'] for change in new_changes]):
        current_pref = [pref for pref in dancer_prefs if pref['name'] == dancer_name][0]
        current_statuses = all_dancer_statuses[dancer_name]
        new_keep_drop = get_keep_drop(current_pref=current_pref, dancer_statuses=current_statuses, metadata=metadata)
        if dancer_name == current_name:
            for mode in ['standard', 'finalize']:
                if mode == request.args['mode']:
                    all_keep_drop[dancer_name][mode] = {'keep_drop': {piece: action for piece, action in keep_drop.items() if action == 'keep'}, 'n_drop': 0}
                else:
                    all_keep_drop[dancer_name][mode] = {'keep_drop': new_keep_drop[mode],
                                                        'n_drop': len([action for piece, action in new_keep_drop[mode].items() if action == 'drop'])}
        else:
            all_keep_drop[dancer_name] = {mode: {'keep_drop': new_keep_drop[mode],
                                                 'n_drop': len([action for piece, action in new_keep_drop[mode].items() if action == 'drop'])}
                                          for mode in ['standard', 'finalize']}

    save_data(data=all_keep_drop, args=request.args, node='all_keep_drop')

    # also need to update statuses
    # dancer_prefs = get_data(args=request.args, node='dancer_prefs')
    # choreographer_prefs = get_data(args=request.args, node='choreographer_prefs')
    # all_cast_statuses = get_all_cast_statuses(cast_list=cast_list)
    # all_dancer_statuses = get_all_dancer_statuses(choreographer_prefs=choreographer_prefs, dancer_prefs=dancer_prefs, all_cast_statuses=all_cast_statuses)
    # save_data(data=all_dancer_statuses, args=request.args, node='all_dancer_statuses')

    # metadata = get_data(args=request.args, node='metadata')
    # all_dancer_validation = get_all_dancer_validation(dancer_prefs=dancer_prefs, all_dancer_statuses=all_dancer_statuses, metadata=metadata)

    return redirect(url_for('keep_drop_calculation', city=request.args['city'], season=request.args['season'], change_direction='next', mode=request.args['mode']))


@app.route('/calculation/drop_all_same_times', methods=['GET'])
def drop_all_same_times_calculation():
    cast_list = get_data(args=request.args, node='cast_list')
    metadata = get_data(args=request.args, node='metadata')
    dancer_prefs = get_data(args=request.args, node='dancer_prefs')
    cast_list, new_changes = drop_all_same_times(metadata=metadata, cast_list=cast_list, dancer_prefs=dancer_prefs)

    save_data(data=cast_list, args=request.args, node='cast_list')

    changes = get_data(args=request.args, node='run_casting_changes')
    changes = new_changes + changes
    save_data(data=changes, args=request.args, node='run_casting_changes')

    all_keep_drop = get_data(args=request.args, node='all_keep_drop')
    choreographer_prefs = get_data(args=request.args, node='choreographer_prefs')
    all_cast_statuses = get_all_cast_statuses(cast_list=cast_list)
    all_dancer_statuses = get_all_dancer_statuses(choreographer_prefs=choreographer_prefs, dancer_prefs=dancer_prefs, all_cast_statuses=all_cast_statuses)
    for dancer_name in set([change['name'] for change in new_changes]):
        current_pref = [pref for pref in dancer_prefs if pref['name'] == dancer_name][0]
        current_statuses = all_dancer_statuses[dancer_name]
        new_keep_drop = get_keep_drop(current_pref=current_pref, dancer_statuses=current_statuses, metadata=metadata)
        all_keep_drop[dancer_name] = {mode: {'keep_drop': new_keep_drop[mode],
                                             'n_drop': len([action for piece, action in new_keep_drop[mode].items() if action == 'drop'])}
                                      for mode in ['standard', 'finalize']}
    save_data(data=all_keep_drop, args=request.args, node='all_keep_drop')

    return redirect(url_for('keep_drop_calculation', city=request.args['city'], season=request.args['season'], change_direction='next', mode=request.args['mode']))


if __name__ == '__main__':
    app.run(debug=True)


# TODO: get rid of code duplication creating all dancer statuses?
