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

    return redirect(url_for('keep_drop_calculation', city=request.args['city'], season=request.args['season'], change_direction='next', mode=request.args['mode']))


@app.route('/calculation/keep_drop', methods=['GET', 'PUT'])
def keep_drop_calculation():
    cast_list = get_data(args=request.args, node='cast_list')
    dancer_prefs = get_data(args=request.args, node='dancer_prefs')
    choreographer_prefs = get_data(args=request.args, node='choreographer_prefs')
    metadata = get_data(args=request.args, node='metadata')

    all_cast_statuses = get_all_cast_statuses(cast_list=cast_list)
    all_dancer_statuses = get_all_dancer_statuses(choreographer_prefs=choreographer_prefs, dancer_prefs=dancer_prefs, all_cast_statuses=all_cast_statuses)

    if 'dancer_name' in request.args.keys():
        next_dancer = request.args['dancer_name']
    else:
        current_dancer_order = get_data(args=request.args, node='run_casting_dancer_order')
        if request.args['change_direction'] == 'next':
            if 'current_name' in request.args.keys() and request.args['current_name'] in current_dancer_order:
                current_dancer_index = current_dancer_order.index(request.args['current_name'])
                if current_dancer_index == len(current_dancer_order) - 1:
                    next_dancer = get_next_dancer_for_casting(current_dancer_order=current_dancer_order, all_dancer_statuses=all_dancer_statuses)
                else:
                    next_dancer = current_dancer_order[current_dancer_index+1]
            else:
                next_dancer = get_next_dancer_for_casting(current_dancer_order=current_dancer_order, all_dancer_statuses=all_dancer_statuses)
        elif request.args['change_direction'] == 'previous':
            if request.args['current_name'] in current_dancer_order:
                current_dancer_index = current_dancer_order.index(request.args['current_name'])
                if current_dancer_index == 0:
                    next_dancer = request.args['current_name']
                else:
                    next_dancer = current_dancer_order[current_dancer_index-1]
            else:
                next_dancer = current_dancer_order[-1]
        else:
            raise ValueError('Need to set change_direction to "next" or "previous" ')

    keep_drop, current_pref, current_statuses = get_dancer_casting_info(dancer_name=next_dancer, dancer_prefs=dancer_prefs,
                                                                        all_dancer_statuses=all_dancer_statuses, metadata=metadata,
                                                                        mode=request.args['mode'])
    changes = get_data(args=request.args, node='run_casting_changes')
    return jsonify({'keep_drop': keep_drop, 'current_pref': current_pref, 'current_statuses': current_statuses, 'changes': changes})


@app.route('/calculation/save_pref_changes', methods=['PUT'])
def save_pref_changes_calculation():
    cast_list = get_data(args=request.args, node='cast_list')
    current_name = request.args['dancer_name']
    keep_drop = json.loads(request.data)['keep_drop']

    cast_list, new_changes = drop_from_list(dancer_name=current_name, cast_list=cast_list, keep_drop=keep_drop)

    save_data(data=cast_list, args=request.args, node='cast_list')

    changes = get_data(args=request.args, node='run_casting_changes')
    changes = new_changes + changes
    save_data(data=changes, args=request.args, node='run_casting_changes')

    current_dancer_order = get_data(args=request.args, node='run_casting_dancer_order')
    current_dancer_order.append(current_name)
    save_data(data=current_dancer_order, args=request.args, node='run_casting_dancer_order')

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

    return redirect(url_for('keep_drop_calculation', city=request.args['city'], season=request.args['season']))


if __name__ == '__main__':
    app.run(debug=True)
