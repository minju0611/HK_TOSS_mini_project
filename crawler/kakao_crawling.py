# 내가 수정함. 

import time
import requests
import pandas as pd
import chromadb
from playwright.sync_api import sync_playwright
from sentence_transformers import SentenceTransformer
import numpy as np
import re

def search_places(keyword, rest_api_key, radius=1000, max_pages=4):
    """카카오 로컬 API를 사용하여 장소를 검색합니다."""
    headers = {"Authorization": f"KakaoAK {rest_api_key}"}
    search_url = "https://dapi.kakao.com/v2/local/search/keyword.json"
    datas = []

    search_word = keyword + " 맛집"
    print(f"🔎 '{search_word}' 검색 중...")

    for page in range(1, max_pages + 1):
        params = {
            "query": search_word,
            "radius": radius,
            "page": page
        }
        response = requests.get(search_url, headers=headers, params=params, timeout=15)
        if response.status_code == 200:
            documents = response.json().get('documents', [])
            datas.extend(documents)
            print(f"✅ 페이지 {page} 검색 완료 ({len(documents)}개 장소)")
        else:
            print(f"⚠️ 검색 실패 (page {page}): {response.status_code}")
            break

    id_place_list = [{'id': data['id'], 'placename': data['place_name']} for data in datas]
    print(f"✅ 총 {len(id_place_list)}개 장소 검색 완료")
    return id_place_list

def scrape_reviews(id_place_list):
    """카카오맵에서 리뷰 데이터를 크롤링합니다."""
    COMMENT_URL = "https://place.map.kakao.com/m/commentlist/v/{}/{}?order=USEFUL&onlyPhotoComment=false"
    all_comment = []

    print("📝 리뷰 크롤링 시작...")
    for idx, id_with_placename in enumerate(id_place_list, 1):
        place_name = id_with_placename['placename']
        place_id = id_with_placename['id']
        comment_id = 0
        has_next = True

        while has_next:
            try:
                scrap_url = COMMENT_URL.format(place_id, comment_id)
                response = requests.get(scrap_url, timeout=15)
                json_response = response.json()
            except Exception as e:
                print(f"⚠️ {place_name} 요청 실패: {e}")
                break

            if 'comment' not in json_response:
                print(f"⚠️ {place_name} 리뷰 없음, 스킵")
                break

            comment_datas = json_response['comment']
            comment_list = comment_datas.get('list', [])

            for comment in comment_list:
                content = comment.get('contents', '').strip()
                point = comment.get('point', None)

                if content:  # 빈 문자열 거르기
                    all_comment.append({
                        '가게이름': place_name,
                        '리뷰내용': content,
                        '리뷰별점': point
                    })

            has_next = comment_datas.get('hasNext', False)
            if has_next and comment_list:
                comment_id = comment_list[-1]['commentid']
            else:
                has_next = False

        time.sleep(1)
        print(f"{place_name} ({idx}/{len(id_place_list)}) 완료! 1초 쉬어요 💤")

    df = pd.DataFrame(all_comment)
    return df


def save_reviews_to_csv(final_df, filename):
    """리뷰 데이터를 CSV 파일로 저장합니다."""
    if final_df.empty:
        print("⚠️ 저장할 데이터가 없습니다.")
        return
        
    final_df = final_df.dropna(subset=['리뷰내용'])
    final_df = final_df[final_df['리뷰내용'].str.strip() != '']
    final_df = final_df.sort_values(by=['가게이름']).reset_index(drop=True)
    final_df.to_csv(filename, index=False, encoding='utf-8-sig')
    print(f"✅ CSV 저장 완료: {filename}")

def open_browser(headless=False):
    """Playwright 브라우저를 시작합니다."""
    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(headless=headless)
    context = browser.new_context()
    page = context.new_page()
    return playwright, browser, context, page

def search_places_ui(page, search_keyword):
    """카카오맵 UI를 통해 장소를 검색합니다."""
    page.goto('https://map.kakao.com/')
    page.wait_for_selector('input#search\\.keyword\\.query')
    
    page.fill('input#search\\.keyword\\.query', search_keyword)
    page.keyboard.press('Enter')
    page.wait_for_selector('ul#info\\.search\\.place\\.list')
    print(f"✅ {search_keyword} 검색 완료")
    
    # dimmedLayer 닫기 (선택 사항)
    try:
        page.wait_for_selector('div#dimmedLayer', timeout=3000)
        page.click('div#dimmedLayer')
        print("✅ dimmedLayer 클릭해서 닫음")
    except:
        print("✅ dimmedLayer 없음")
    
    return page

def extract_store_basic_info(new_page):
    """가게 기본 정보를 추출합니다."""
    store_info = {
        'store_name': None,
        'address': None,
        'phone': None
    }
    
    # 가게 이름
    try:
        store_name_raw = new_page.inner_text('h3.tit_place')
        store_info['store_name'] = store_name_raw.replace("장소명", "").strip()
        print(f"🏢 가게 이름: {store_info['store_name']}")
    except:
        print("❌ 가게 이름 추출 실패")
        
    # 가게 주소
    try:
        store_info['address'] = new_page.inner_text('div.row_detail span.txt_detail')
        print(f"📍 주소: {store_info['address']}")
    except:
        print("❌ 주소 추출 실패")
        
    # 전화번호
    try:
        store_info['phone'] = new_page.inner_text('div.detail_info.info_suggest span.txt_detail')
        print(f"☎️ 전화번호: {store_info['phone']}")
    except:
        print("❌ 전화번호 추출 실패")
    
    return store_info

def extract_store_open_hours(new_page):
    """가게 영업시간 정보를 추출합니다."""
    openhours = {}
    try:
        elements = new_page.query_selector_all('div#foldDetail2 div.line_fold')
        for elem in elements:
            day_span = elem.query_selector('span.tit_fold')
            if not day_span:
                continue
                
            day = day_span.inner_text().strip()
            open_info = {'영업시간': None, '라스트오더': None, '브레이크타임': None}
            
            detail_fold = elem.query_selector('div.detail_fold')
            if detail_fold:
                details = detail_fold.query_selector_all('span.txt_detail')
                for idx2, detail in enumerate(details):
                    text = detail.inner_text().strip()
                    if idx2 == 0:
                        open_info['영업시간'] = text
                    else:
                        if '라스트오더' in text:
                            open_info['라스트오더'] = text.replace('라스트오더', '').replace('~', '').strip()
                        elif '브레이크타임' in text:
                            open_info['브레이크타임'] = text.replace('브레이크타임', '').strip()
            else:
                open_info['영업시간'] = '정보 없음'
                
            openhours[day] = open_info
        print(f"🕒 영업시간 정보 추출 완료")
    except:
        openhours = {}
        print("❌ 영업시간 정보 추출 실패")
    
    return openhours

def extract_store_facilities(new_page):
    """가게 시설 정보를 추출합니다."""
    # 정보 탭 클릭
    try:
        info_tab = new_page.query_selector('a.link_tab[role="tab"]:has-text("정보")')
        if info_tab:
            info_tab.click()
            new_page.wait_for_selector('div.default_info.type_descinfo', timeout=3000)
            print("✅ 정보 탭 클릭 완료")
    except:
        print("❌ 정보 탭 클릭 실패")
    
    # 시설정보
    facilities = []
    try:
        unit_defaults = new_page.query_selector_all('div.unit_default')
        for unit in unit_defaults:
            title = unit.query_selector('span.ico_mapdesc.ico_facilities')
            if title:
                detail_area = unit.query_selector('div.row_detail.aligntype_gap')
                if detail_area:
                    badges = detail_area.query_selector_all('span.badge_label')
                    facilities = [badge.inner_text().strip() for badge in badges]
                break
        print(f"🏢 시설정보: {facilities}")
    except:
        print("❌ 시설정보 추출 실패")
    
    return facilities

def extract_store_hashtags(new_page):
    """가게 해시태그를 추출합니다."""
    hashtags = []
    try:
        unit_defaults = new_page.query_selector_all('div.unit_default')
        for unit in unit_defaults:
            title = unit.query_selector('span.ico_mapdesc.ico_hashtag')
            if title:
                detail_area = unit.query_selector('div.row_detail')
                if detail_area:
                    tags = detail_area.query_selector_all('a.txt_detail')
                    hashtags = [tag.inner_text().strip() for tag in tags]
                break
        print(f"# 해시태그: {hashtags}")
    except:
        print("❌ 해시태그 추출 실패")
    
    return hashtags

def extract_store_categories(new_page):
    """가게 카테고리를 추출합니다."""
    categories = []
    try:
        category_span = new_page.query_selector('span.info_cate')
        if category_span:
            screen_out_span = category_span.query_selector('span.screen_out')
            screen_out_text = screen_out_span.inner_text().strip() if screen_out_span else ''
            full_text = category_span.inner_text().strip()
            category_text = full_text.replace(screen_out_text, '').strip()
            if category_text:
                categories = [cat.strip() for cat in category_text.split(',')]
        print(f"🏷️ 카테고리: {categories}")
    except:
        print("❌ 카테고리 추출 실패")
    
    return categories

def extract_store_main_image(new_page):
    """가게 대표 이미지를 추출합니다."""
    main_image_url = None
    try:
        photo_tab = new_page.query_selector('a[role="tab"]:has-text("사진")')
        if photo_tab:
            photo_tab.click()
            new_page.wait_for_timeout(2000)
            print("✅ 사진 탭 클릭 완료")
            
        first_photo = new_page.query_selector('div.view_photolist ul.list_photo li a img')
        if first_photo:
            src = first_photo.get_attribute('src')
            if src:
                main_image_url = src
                print(f"🖼️ 대표 사진 URL 추출 완료")
    except:
        print("❌ 대표 사진 추출 실패")
    
    return main_image_url

def extract_store_menus(new_page, store_id, store_name):
    """가게 메뉴 정보를 추출합니다."""
    menus_data = []
    store_menu_data = []
    try:
        menu_tab = new_page.query_selector('a[role="tab"]:has-text("메뉴")')
        if menu_tab:
            menu_tab.click()
            new_page.wait_for_timeout(2000)
            print("✅ 메뉴 탭 클릭 완료")
            
        menu_items = new_page.query_selector_all('ul.list_goods > li')
        for item in menu_items:
            img_tag = item.query_selector('a.link_thumb img')
            image_url = img_tag.get_attribute('src') if img_tag else None
            
            title_tag = item.query_selector('strong.tit_item')
            title = title_tag.inner_text().strip() if title_tag else None
            
            price_tag = item.query_selector('p.desc_item')
            price = price_tag.inner_text().strip() if price_tag else None
            
            desc_tag = item.query_selector('p.desc_item2')
            description = desc_tag.inner_text().strip() if desc_tag else None
            
            menus_data.append({
                'store_id': store_id,
                'menu_name': title,
                'price': price,
                'description': description,
                'image_url': image_url
            })
            
            # 두 번째 코드의 형식에 맞게 데이터도 추가
            store_menu_data.append({
                '가게이름': store_name,
                '메뉴명': title,
                '가격': price
            })
            
        print(f"🍽️ {len(store_menu_data)}개 메뉴 정보 추출 완료")
    except:
        print("❌ 메뉴 추출 실패")
    
    return menus_data, store_menu_data

def crawl_store_detail(context, store_item, store_id, max_store_id, crawled_stores_count):
    """개별 가게의 세부 정보를 크롤링합니다."""
    store_data = None
    menus_data = []
    
    new_page = None
    try:
        # 상세보기 링크 클릭
        more_view_button = store_item.query_selector('a.moreview')
        if more_view_button:
            with context.expect_page() as new_page_info:
                more_view_button.click()
            new_page = new_page_info.value
            print("✅ 상세보기 페이지 열림")
            
            # 상세 페이지 로딩 대기
            new_page.wait_for_selector('h3.tit_place', timeout=10000)
            
            # 기본 정보 추출
            store_info = extract_store_basic_info(new_page)
            
            # 영업시간 정보 추출
            openhours = extract_store_open_hours(new_page)
            
            # 시설 정보, 해시태그, 카테고리 추출
            facilities = extract_store_facilities(new_page)
            hashtags = extract_store_hashtags(new_page)
            categories = extract_store_categories(new_page)
            
            # 대표 사진 추출
            main_image_url = extract_store_main_image(new_page)
            
            # 메뉴 정보 추출
            menus_info, store_menu_data = extract_store_menus(new_page, store_id, store_info['store_name'])
            
            # 가게 데이터 저장
            store_data = {
                'store_id': store_id,
                'store_name': store_info['store_name'],
                'address': store_info['address'],
                'phone': store_info['phone'],
                'openhours': str(openhours),  # 딕셔너리를 문자열로 변환
                'facilities': str(facilities),  # 리스트를 문자열로 변환
                'hashtags': str(hashtags),  # 리스트를 문자열로 변환
                'categories': str(categories),  # 리스트를 문자열로 변환
                'main_image_url': main_image_url
            }
            
            menus_data = store_menu_data
            
            # 새 페이지 닫기
            new_page.close()
            print(f"✅ {crawled_stores_count+1}번째 가게 크롤링 완료")
            
        else:
            print("⚠️ 상세보기 버튼을 찾을 수 없습니다.")
            
    except Exception as e:
        print(f"❌ 가게 크롤링 실패: {e}")
        if new_page and not new_page.is_closed():
            new_page.close()
    
    return store_data, menus_data

def navigate_to_next_page(page, current_page, more_button_clicked):
    """다음 페이지로 이동합니다."""
    next_page_success = False
    
    # 3페이지까지는 첫번째 로직, 그 이후는 두번째 로직 사용
    if current_page < 3:
        # 첫번째 로직
        if not more_button_clicked:
            try:
                more_button_selector = '#info\\.search\\.place\\.more'
                page.wait_for_selector(more_button_selector, timeout=5000)
                page.click(more_button_selector)
                print("➡️ '장소 더보기' 버튼 클릭")
                page.wait_for_selector('ul#info\\.search\\.place\\.list', timeout=10000)
                time.sleep(2)
                next_page_success = True
                return 1, True, next_page_success
            except Exception as e:
                print(f"⚠️ '장소 더보기' 버튼 없음 또는 클릭 실패: {e}")
                return current_page, more_button_clicked, next_page_success
        else:
            next_page = current_page + 1
            try:
                next_page_selector = f'#info\\.search\\.page\\.no{next_page}'
                page.wait_for_selector(next_page_selector, timeout=5000)
                page.click(next_page_selector)
                print(f"➡️ 페이지 {next_page} 클릭 (첫번째 로직)")
                page.wait_for_selector('ul#info\\.search\\.place\\.list', timeout=10000)
                time.sleep(2)
                next_page_success = True
                return next_page, more_button_clicked, next_page_success
            except Exception as e:
                print(f"⚠️ {next_page} 페이지 버튼 없음 또는 클릭 실패: {e}")
                return current_page, more_button_clicked, next_page_success
    else:
        # 두번째 로직
        next_page = current_page + 1
        try:
            next_page_selector = f'#info\\.search\\.page\\.no{next_page}'
            page.wait_for_selector(next_page_selector, timeout=5000)
            page.click(next_page_selector)
            print(f"➡️ 페이지 {next_page} 클릭 (두번째 로직)")
            page.wait_for_selector('ul#info\\.search\\.place\\.list', timeout=10000)
            time.sleep(2)
            next_page_success = True
            return next_page, more_button_clicked, next_page_success
        except Exception as e:
            print(f"⚠️ 페이지 {next_page} 버튼 없음 또는 클릭 실패: {e}")
            # 페이지가 없으면 '다음' 버튼을 시도
            try:
                next_button_selector = '#info\\.search\\.page\\.next'
                page.wait_for_selector(next_button_selector, timeout=5000)
                page.click(next_button_selector)
                print("➡️ '다음' 버튼 클릭")
                page.wait_for_selector('ul#info\\.search\\.place\\.list', timeout=10000)
                time.sleep(2)
                next_page_success = True
                # 다음 버튼을 클릭하면 페이지 번호가 1로 변경됨
                return 1, more_button_clicked, next_page_success
            except Exception as e2:
                print(f"⚠️ '다음' 버튼 없음 또는 클릭 실패: {e2}")
                return current_page, more_button_clicked, next_page_success

def crawl_places_ui(search_keyword, max_store_id=50):
    """카카오맵 UI를 통해 장소 정보를 크롤링합니다."""
    playwright, browser, context, page = open_browser(headless=False)
    
    try:
        # 카카오맵 검색
        page = search_places_ui(page, search_keyword)
        
        # 데이터 저장용 리스트
        stores_data = []
        menus_data = []
        store_id = 1                # 가게 고유 번호
        more_button_clicked = False # 장소 더보기 버튼 클릭 여부
        current_page = 1    # 현재 페이지 번호
        crawled_stores_count = 0 # 크롤링 완료한 가게 수
        
        while crawled_stores_count < max_store_id:
            print(f"\n--- 현재까지 {crawled_stores_count}개 가게 크롤링 완료 (현재 페이지: {current_page}) ---")
            
            # 현재 페이지의 모든 가게 목록 가져오기
            page.wait_for_selector('ul#info\\.search\\.place\\.list li')
            store_items = page.query_selector_all('ul#info\\.search\\.place\\.list li')
            print(f"✅ 현재 페이지에 {len(store_items)}개의 가게 발견")
            
            # 현재 페이지의 각 가게 크롤링
            for i, store_item in enumerate(store_items):
                if crawled_stores_count >= max_store_id:
                    break
                    
                store_index_on_page = i + 1
                print(f"\n--- {crawled_stores_count + 1}번째 가게 (현재 페이지 순번 {store_index_on_page}) 크롤링 시작 ---")
                
                store_data, store_menus = crawl_store_detail(
                    context, store_item, store_id, max_store_id, crawled_stores_count
                )
                
                if store_data:
                    stores_data.append(store_data)
                    menus_data.extend(store_menus)
                    store_id += 1
                    crawled_stores_count += 1
                
                # 잠시 대기
                time.sleep(1)
            
            # 모든 가게를 크롤링했으면 종료
            if crawled_stores_count >= max_store_id:
                break
                
            # 페이징 처리
            current_page, more_button_clicked, next_page_success = navigate_to_next_page(
                page, current_page, more_button_clicked
            )
            
            if not next_page_success:
                break
        
        # 결과 반환
        return stores_data, menus_data
        
    finally:
        # 브라우저 종료
        browser.close()
        playwright.stop()

def save_data_to_csv(data_list, filename):
    """데이터를 CSV 파일로 저장합니다."""
    if not data_list:
        print(f" '{filename}'에 저장할 데이터가 없습니다.")
        return
        
    try:
        pd.DataFrame(data_list).to_csv(filename, encoding='utf-8-sig', index=False)
        print(f" 데이터를 '{filename}'로 저장했습니다.")
    except Exception as e:
        print(f" '{filename}' 저장 실패: {e}")



def main():
    """메인 실행 함수"""
    print("🍽️ 카카오맵 데이터 수집 시스템을 시작합니다")
    
    # 설정값
    REST_API_KEY = ""  # 카카오 API 키
    max_store_count = 50  # 최대 크롤링할 가게 수
    
    # 검색 키워드 입력 받기
    keyword = input("역 이름을 입력하세요 (예: 충정로역): ").strip()
    search_keyword = f"{keyword} 맛집"
    
    # 1. API로 장소 검색 (기존 첫 번째 스크립트의 함수 호출)
    print("\n==== 1단계: 카카오 API로 장소 검색 ====")
    id_place_list = search_places(keyword, REST_API_KEY)
    
    # 2. API로 리뷰 크롤링 (기존 첫 번째 스크립트의 함수 호출)
    print("\n==== 2단계: 리뷰 크롤링 ====")
    reviews_df = scrape_reviews(id_place_list)
    
    # 4. UI로 가게와 메뉴 정보 크롤링 (기존 두 번째 스크립트의 함수 호출)
    print("\n==== 4단계: 가게 및 메뉴 정보 크롤링 ====")
    stores_data, menus_data = crawl_places_ui(search_keyword, max_store_count)
    
    # 5. 데이터 저장
    print("\n==== 5단계: 데이터 저장 ====")
    # 리뷰 데이터 CSV 저장
    reviews_filename = f"{keyword}_리뷰데이터.csv"
    save_reviews_to_csv(reviews_df, reviews_filename)
    
    # 가게 정보 CSV 저장
    safe_keyword = re.sub(r'[^\w\s]', '', search_keyword).replace(' ', '_')
    stores_filename = f"{safe_keyword}_stores.csv"
    save_data_to_csv(stores_data, stores_filename)
    
    # 메뉴 정보 CSV 저장
    menus_filename = f"{safe_keyword}_menus.csv"
    save_data_to_csv(menus_data, menus_filename)

    
    print("\n 모든 작업이 완료되었습니다!")
    print(f"CSV 파일 저장 위치: {reviews_filename}, {stores_filename}, {menus_filename}")

if __name__ == "__main__":
    main()
