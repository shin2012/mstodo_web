@app.route('/api/lists')
def get_lists():
    token_data = get_refreshed_token()
    if not token_data: return jsonify({"error": "Not authenticated"}), 401
    
    try:
        access_token = token_data.get('access_token')
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # 1. 목록 그룹(List Groups) 가져오기 (Beta API)
        groups_url = "https://graph.microsoft.com/beta/me/todo/listGroups"
        groups_resp = requests.get(groups_url, headers=headers)
        group_map = {}
        if groups_resp.status_code == 200:
            for g in groups_resp.json().get('value', []):
                group_map[g['id']] = {'name': g['displayName'], 'lists': []}

        # 2. 할 일 목록(Lists) 가져오기 (Beta API - 그룹 ID 포함됨)
        lists_url = "https://graph.microsoft.com/beta/me/todo/lists"
        grouped_data = {"ungrouped": []}
        
        while lists_url:
            resp = requests.get(lists_url, headers=headers)
            if resp.status_code != 200: break
            data = resp.json()
            for l in data.get('value', []):
                list_obj = {
                    'id': l['id'], 
                    'name': l['displayName'], 
                    'wellKnownName': l.get('wellKnownName', 'none')
                }
                # 그룹 ID가 있는지 확인
                group_id = l.get('listGroupId')
                if group_id and group_id in group_map:
                    if group_id not in grouped_data:
                        grouped_data[group_id] = {"name": group_map[group_id]['name'], "lists": []}
                    grouped_data[group_id]["lists"].append(list_obj)
                else:
                    grouped_data["ungrouped"].append(list_obj)
            lists_url = data.get('@odata.nextLink')

        print(f"DEBUG: Returning {len(grouped_data)} groups")
        return jsonify(grouped_data)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
