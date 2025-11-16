from flask import Flask, render_template, request,flash, redirect, url_for, session, jsonify
from database import DBhandler
import hashlib
import sys

application = Flask(__name__)
application.config["SECRET_KEY"] = "helloosp"
DB = DBhandler()

@application.route("/")
def hello():
    return redirect(url_for('view_list'))

@application.route("/list")
def view_list():
    page = request.args.get("page", 0, type=int)
    per_page=8
    per_row=4
    row_count=int(per_page/per_row)
    start_idx=per_page*page
    end_idx=per_page*(page+1)

    data = DB.get_item_list()
    item_counts = len(data)

    data_0 = {}
    data_1 = {}
    if item_counts > 0:
    # 상품이 있는 경우에만 페이징 처리 및 행 분할 로직 실행
        data = dict(list(data.items())[start_idx:end_idx])
        tot_count = len(data)
    
    for i in range(row_count):
        # 상품 분할 로직은 그대로 유지하되, locals() 대신 명시적인 변수에 할당
        current_data = dict(list(data.items())[i*per_row:] if (i == row_count-1) and (tot_count%per_row != 0)
                            else dict(list(data.items())[i*per_row:(i+1)*per_row]))
        
        # i 값에 따라 동적으로 할당하는 대신 명시적 변수에 할당 (코드 가독성 및 안전성 확보)
        if i == 0:
            data_0 = current_data
        elif i == 1:
            data_1 = current_data
    return render_template (
        "items.html", 
        datas=data.items(), 
        row1 = locals()['data_0'].items(),
        row2 = locals()['data_1'].items(),
        limit=per_page,
        page=page,
        page_count=int((item_counts/per_page)+1),
        total=item_counts
    )    


@application.route('/view_detail/<name>/')
def view_item_detail(name):
    print("###name:",name)
    data = DB.get_item_byname(str(name))
    print("###data:",data)
    seller_nickname = DB.get_user_nickname(data.get('seller'))
    return render_template("item_detail.html", name=name, data=data, nickname=seller_nickname)

# 상품등록 페이지 반환 (reg_items.html)
@application.route("/reg_items")
def reg_item():
    if 'id' not in session or not session['id']:
            flash('로그인을 해주세요.')
            return redirect(url_for('login'))
    else:
        return render_template("reg_items.html")

# reg_items.html에 입력한 값들 db에저정 -> 상품상세 페이지 념겨줌
@application.route("/submit_item_post", methods=['POST'])
def reg_item_submit_post():
    image_file=request.files["file"]
    image_file.save("static/images/{}".format(image_file.filename))
    data=request.form
    DB.insert_item(data['name'], data, image_file.filename, session['id'])
    
    return redirect(url_for('view_item_detail', name=data['name']))

@application.route("/reg_reviews")
#def reg_review():
#    return render_template("reg_reviews.html")
# 12주차 리뷰 등록을 위한 경로

# 12주차 리뷰 등록을 위한 경로 추가 시작
@application.route("/reg_review_init/<name>/")
def reg_review_init(name):
    return render_template("reg_reviews.html", name=name)
@application.route("/reg_review", methods=['POST'])
def reg_review():
    print(request.form)
    form_data=request.form
    try:
        image_file = request.files["photos"] # HTML에 맞춰 "photos"로 변경
        
        # 파일이 존재하고 파일명이 있는 경우에만 저장 및 경로 설정
        if image_file.filename:
            image_file.save("static/images/{}".format(image_file.filename))
            img_path = image_file.filename
        else:
            img_path = ""
    except KeyError:
        # 파일 필드가 아예 없거나 잘못된 경우 처리
        img_path = ""
    
    # DB 핸들러를 사용하여 리뷰 정보를 저장합니다.
    mapped_data = {
        "name": form_data['name'], # 상품 이름 (DB child key)
        "title": form_data['title'],
        "reviewStar": form_data['rating'], # 별점 매핑
        "reviewContents": form_data['content'] # 내용 매핑
    }
    DB.reg_review(mapped_data, img_path)
    
    # 저장 후 전체 리뷰 목록 페이지로 이동합니다. (기존 /reviews 경로 사용) [5]
    return redirect(url_for('view_review'))
# 12주차 리뷰 등록을 위한 경로 추가 끝
# 12주차 리뷰 조회를 위한 경로 추가 시작
@application.route("/reviews")
def view_review():
    page = request.args.get("page", 0, type=int)
    per_page=6 
    per_row=3 
    row_count=int(per_page/per_row)
    start_idx=per_page*page
    end_idx=per_page*(page+1)
    data = DB.get_reviews() 
    item_counts = len(data)
    data_list = list(data.items())
    data_paged = dict(data_list[start_idx:end_idx])
    locals_data = {}
    tot_count = len(data_paged)

    for i in range(row_count):
        start = i * per_row
        end = (i + 1) * per_row
        
        # 마지막 줄이 per_row보다 적은 경우를 처리
        if i == row_count - 1 and tot_count % per_row != 0:
            current_data = dict(data_list[start_idx + start:])
        else:
            current_data = dict(data_list[start_idx + start: start_idx + end])
        
        locals_data[f'data_{i}'] = current_data

    return render_template(
        "reviews.html",
        # data_0, data_1을 reviews.html에 row1, row2로 전달
        row1=locals_data.get('data_0', {}).items(), 
        row2=locals_data.get('data_1', {}).items(),
        limit=per_page,
        page=page,
        # 전체 페이지 개수 계산 (ceil(total/per_page))
        page_count=int((item_counts + per_page - 1) / per_page), 
        total=item_counts
    )

@application.route('/view_review_detail/<name>/')
def view_review_detail(name):
    # 상품 이름을 키로 사용하여 리뷰 데이터 가져오기 (12주차 reg_review 방식)
    review_data = DB.db.child("review").child(str(name)).get().val()
    
    # 상품 이름은 review_data에는 포함되지 않으므로 별도 변수로 전달
    product_name = name 
    
    # 리뷰 작성자 닉네임을 가져오는 로직 (작성자 ID가 리뷰 데이터에 있다면)
    # 현재 reg_review에는 buyerID가 없으므로 임시로 빈값으로 처리하거나, 
    # 만약 buyerID를 포함하도록 reg_review를 수정했다면 그 정보를 사용
    # 여기서는 data.get('buyerID')가 없다고 가정하고 닉네임은 임시로 None으로 설정
    nickname = None 
    
    if review_data:
        # DB에서 가져온 리뷰 데이터는 상품 이름(name)을 key로 가진다.
        # review_detail.html 템플릿에 필요한 데이터를 전달
        return render_template("review_detail.html", 
                                name=product_name, # 상품 이름
                                data=review_data,  # 리뷰 내용 (title, rate, review, img_path)
                                nickname=nickname)
    else:
        # 리뷰가 존재하지 않는 경우 처리
        flash(f"'{name}'에 대한 리뷰가 없습니다.")
        return redirect(url_for('view_review'))
# 12주차 리뷰 조회를 위한 경로 추가 끝



@application.route("/reviews_by_item")
def view_review_by_item():
    return render_template("reviews_by_item.html")

@application.route("/login")
def login():
    return render_template("login.html")

@application.route("/login_confirm", methods=['POST'])
def login_user():
    id_=request.form['id']
    pw=request.form['pw']
    pw_hash = hashlib.sha256(pw.encode('utf-8')).hexdigest()
    if DB.find_user(id_,pw_hash):
        session['id']=id_
        return redirect(url_for('view_list'))
    else:
        flash("Wrong ID or PW!")
        return render_template("login.html")

@application.route("/signup")
def signup():
    return render_template("signup.html")

@application.route("/signup_post", methods=['POST'])
def register_user():
    data=request.form
    pw=request.form['pw']
    pw_hash = hashlib.sha256(pw.encode('utf-8')).hexdigest()
    if DB.insert_user(data,pw_hash):
        return render_template("login.html")
    else:
        flash("user id already exist!")
        return render_template("signup.html")
    
@application.route("/logout")
def logout_user():
    session.clear()
    return redirect(url_for('view_list'))

# 12주차 좋아요 기능
@application.route('/show_heart/<name>/', methods=['GET'])
def show_heart(name):
    my_heart = DB.get_heart_byname(session['id'],name)
    return jsonify({'my_heart': my_heart})
@application.route('/like/<name>/', methods=['POST'])
def like(name):
    my_heart = DB.update_heart(session['id'],'Y',name)
    return jsonify({'msg': '좋아요 완료!'})
@application.route('/unlike/<name>/', methods=['POST'])
def unlike(name):
    my_heart = DB.update_heart(session['id'],'N',name)
    return jsonify({'msg': '안좋아요 완료!'})


#마이페이지 관련 코드 
@application.route("/mypage")
def mypage():
    return render_template("mypage/mypage.html")

@application.route("/mypage_edit")
def mypage_edit():
    return render_template("mypage/mypage_edit.html")

@application.route("/mypage_buy")
def mypage_buy():
    return render_template("mypage/mypage_buy.html")

@application.route("/mypage_sell")
def mypage_sell():
    return render_template("mypage/mypage_sell.html")

@application.route("/mypage_sell_edit")
def mypage_sell_edit():
    return render_template("mypage/mypage_sell_edit.html")

@application.route("/mypage_like")
def mypage_like():
    return render_template("mypage/mypage_like.html")

@application.route("/mypage_review")
def mypage_review():
    return render_template("mypage/mypage_review.html")

@application.route("/mypage_review_edit")
def mypage_review_edit():
    return render_template("mypage/mypage_review_edit.html")

if __name__ == "__main__":
    application.run(host='0.0.0.0')




