import asyncio
import os
import random
import sys
import pygame

# --- 初期化 ---
pygame.init()
SCREEN_WIDTH, SCREEN_HEIGHT = 800, 600
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Food Stand Management Simulation")

# 食材10種
INGREDIENTS = [
    "Beef",
    "Pork",
    "Chicken",
    "Cabbage",
    "Cheese",
    "Tomato",
    "Bread",
    "Rice",
    "Egg",
    "Spice",
]


class GameState:

  def __init__(self):
    self.day = 1
    self.money = 3000  # 初期資金
    self.customers_count = 3  # 初日は3人スタート
    self.customer_orders = []
    self.customer_servings = {}
    self.active_customer_idx = 0

    # 各食材の在庫（初期は各5個）と購入価格
    self.inventory = {ing: 5 for ing in INGREDIENTS}
    self.ingredient_price = 150

    self.state = "SELECT"  # 'SELECT', 'RESULT', 'SHOP'
    self.today_reports = []
    self.today_revenue = 0
    self.today_fixed_cost = 1200
    self.today_random_cost = 0
    self.today_total_cost = 0

    self.game_over = False
    self.game_clear = False


game = GameState()
clock = pygame.time.Clock()

font = pygame.font.Font(None, 22)
title_font = pygame.font.Font(None, 28)
small_font = pygame.font.Font(None, 16)

# 画像キャッシュ用の辞書
image_cache = {}


def load_dish_image(serving_list):
  """3つの食材から画像パスを生成し、画像をロードする"""
  if len(serving_list) != 3:
    return None

  # 順番に関係なく一意になるようソートしてファイル名を結合
  sorted_items = sorted(serving_list)
  file_name = f"{sorted_items[0]}_{sorted_items[1]}_{sorted_items[2]}.jpg"
  file_path = os.path.join("data", file_name)

  if file_path in image_cache:
    return image_cache[file_path]

  try:
    if os.path.exists(file_path):
      img = pygame.image.load(file_path).convert()
      img = pygame.transform.scale(img, (200, 200))  # 表示用にリサイズ
      image_cache[file_path] = img
      return img
    else:
      image_cache[file_path] = None
      return None
  except Exception:
    image_cache[file_path] = None
    return None


def prepare_day():
  """その日の客の人数分だけ注文をランダム生成する（最大5人まで）"""
  game.customer_orders = []
  game.customer_servings = {}
  if game.customers_count > 5:
    game.customers_count = 5

  for i in range(game.customers_count):
    wants = random.sample(INGREDIENTS, 3)
    game.customer_orders.append({"id": i + 1, "wants": wants})
    game.customer_servings[i + 1] = []
  game.active_customer_idx = 0


prepare_day()


def run_day_simulation():
  """営業シミュレーションと在庫の消費"""
  total_used = {}
  for c_id, served in game.customer_servings.items():
    for item in served:
      total_used[item] = total_used.get(item, 0) + 1

  for item, count in total_used.items():
    game.inventory[item] = max(0, game.inventory[item] - count)

  game.today_reports = []
  total_score = 0
  sold_count = 0

  for order in game.customer_orders:
    c_id = order["id"]
    wants = order["wants"]
    served = game.customer_servings.get(c_id, [])

    matches = len(set(served) & set(wants))

    if matches == 3:
      score = random.randint(85, 100)
      comment = "Perfect! Exactly what I wanted!"
      sold_count += 1
    elif matches == 2:
      score = random.randint(60, 84)
      comment = "Good, pretty tasty."
      sold_count += 1
    elif matches == 1:
      score = random.randint(30, 59)
      comment = "Normal... a bit different."
      sold_count += 0.5
    else:
      score = random.randint(0, 29)
      comment = "Bad... not my taste."

    total_score += score
    game.today_reports.append({
        "id": c_id,
        "wants": ", ".join(wants),
        "served": ", ".join(served) if served else "None",
        "score": score,
        "comment": comment,
    })

  game.today_revenue = int(sold_count * 600)
  game.today_fixed_cost = 1200
  game.today_random_cost = random.randint(0, 800)
  game.today_total_cost = game.today_fixed_cost + game.today_random_cost

  game.money += game.today_revenue - game.today_total_cost

  avg_score = total_score / max(1, game.customers_count)
  if avg_score >= 70:
    game.customers_count = min(5, game.customers_count + 1)
  elif avg_score < 40:
    game.customers_count = max(2, game.customers_count - 1)


# --- メインループ（async対応） ---
async def main():
  running = True

  while running:
    screen.fill((240, 240, 240))

    for event in pygame.event.get():
      if event.type == pygame.QUIT:
        running = False

      if event.type == pygame.MOUSEBUTTONDOWN and not (
          game.game_over or game.game_clear
      ):
        mx, my = event.pos

        if game.state == "SELECT":
          # 1. タブ切り替え
          for i in range(len(game.customer_orders)):
            tx = 30 + i * 148
            if tx <= mx <= tx + 140 and 70 <= my <= 145:
              game.active_customer_idx = i

          current_c_id = game.customer_orders[game.active_customer_idx]["id"]
          current_serving = game.customer_servings[current_c_id]

          # 2. 食材ボタン（描画と一致させるため幅105、間隔115に修正）
          if 175 <= my <= 220:
            for i in range(5):
              bx = 50 + i * 115
              if bx <= mx <= bx + 105:
                item = INGREDIENTS[i]
                if item in current_serving:
                  current_serving.remove(item)
                elif len(current_serving) < 3 and game.inventory[item] > 0:
                  current_serving.append(item)
                break
          elif 255 <= my <= 300:
            for i in range(5):
              bx = 50 + i * 115
              if bx <= mx <= bx + 105:
                item = INGREDIENTS[i + 5]
                if item in current_serving:
                  current_serving.remove(item)
                elif len(current_serving) < 3 and game.inventory[item] > 0:
                  current_serving.append(item)
                break

          # 3. 状態の判定（全員分揃っているか ＆ 在庫超過がないか）
          all_ready = all(
              len(game.customer_servings[o["id"]]) == 3
              for o in game.customer_orders
          )

          total_used = {}
          for c_id, served in game.customer_servings.items():
            for item in served:
              total_used[item] = total_used.get(item, 0) + 1

          stock_shortage = any(
              count > game.inventory[item] for item, count in total_used.items()
          )
          can_start = all_ready and not stock_shortage

          if 300 <= mx <= 550 and 500 <= my <= 560 and can_start:
            run_day_simulation()
            game.state = "RESULT"

        elif game.state == "RESULT":
          # 「Go to Shop」ボタン
          if 300 <= mx <= 550 and 520 <= my <= 580:
            if game.money < 0:
              game.game_over = True
            else:
              game.state = "SHOP"

        elif game.state == "SHOP":
          # 食材購入ボタンの判定 (10種)
          if 175 <= my <= 220:
            for i in range(5):
              bx = 50 + i * 135
              if bx <= mx <= bx + 120:
                item = INGREDIENTS[i]
                if game.money >= game.ingredient_price:
                  game.money -= game.ingredient_price
                  game.inventory[item] += 1
                break
          elif 255 <= my <= 300:
            for i in range(5):
              bx = 50 + i * 135
              if bx <= mx <= bx + 120:
                item = INGREDIENTS[i + 5]
                if game.money >= game.ingredient_price:
                  game.money -= game.ingredient_price
                  game.inventory[item] += 1
                break

          # 「Next Day」ボタン
          if 300 <= mx <= 550 and 500 <= my <= 550:
            if game.day >= 10:
              game.game_clear = True
            else:
              game.day += 1
              prepare_day()
              game.state = "SELECT"

    # --- 描画処理 ---
    if game.game_over:
      screen.fill((50, 0, 0))
      over_txt = title_font.render(
          "GAME OVER (Bankrupt)...", True, (255, 255, 255)
      )
      screen.blit(over_txt, (220, 250))
    elif game.game_clear:
      screen.fill((0, 50, 0))
      clear_txt = title_font.render(
          "GAME CLEAR! (Survived 10 Days)", True, (255, 255, 255)
      )
      screen.blit(clear_txt, (200, 250))
    else:
      # 上部ステータス表示
      status_txt = title_font.render(
          f"Day: {game.day}/10 | Funds: {game.money}G | Customers Today:"
          f" {game.customers_count}",
          True,
          (20, 20, 20),
      )
      screen.blit(status_txt, (30, 15))

      if game.state == "SELECT":
        guide_header = font.render(
            "Check orders & select ingredients (Stock required):",
            True,
            (50, 50, 50),
        )
        screen.blit(guide_header, (30, 45))

        # 客ごとのタブを描画
        for i, order in enumerate(game.customer_orders):
          c_id = order["id"]
          wants = order["wants"]
          served_count = len(game.customer_servings[c_id])

          tx = 30 + i * 148
          ty = 70
          is_active = i == game.active_customer_idx

          if is_active:
            tab_color = (100, 200, 255)
          elif served_count == 3:
            tab_color = (200, 255, 200)
          else:
            tab_color = (220, 220, 220)

          pygame.draw.rect(
              screen, tab_color, (tx, ty, 140, 75), border_radius=6
          )
          pygame.draw.rect(
              screen, (50, 50, 50), (tx, ty, 140, 75), 2, border_radius=6
          )

          t_txt = small_font.render(
              f"Customer #{c_id} ({served_count}/3)", True, (10, 10, 10)
          )
          w1_txt = small_font.render(
              f"Wants: {wants[0]}, {wants[1]}", True, (60, 60, 60)
          )
          w2_txt = small_font.render(f"       {wants[2]}", True, (60, 60, 60))

          screen.blit(t_txt, (tx + 6, ty + 6))
          screen.blit(w1_txt, (tx + 6, ty + 26))
          screen.blit(w2_txt, (tx + 6, ty + 44))

        active_order = game.customer_orders[game.active_customer_idx]
        active_serving = game.customer_servings[active_order["id"]]

        cur_text = font.render(
            f"Cooking for Customer #{active_order['id']} | Selected:"
            f" {', '.join(active_serving) if active_serving else 'None'}",
            True,
            (0, 100, 200),
        )
        screen.blit(cur_text, (30, 315))

        # 食材ボタン描画
        for i, ing in enumerate(INGREDIENTS):
          row = 0 if i < 5 else 1
          col = i % 5
          bx = 50 + col * 115
          by = 175 + row * 80

          stock = game.inventory[ing]
          if stock == 0:
            color = (220, 180, 180)
          elif ing in active_serving:
            color = (100, 220, 100)
          else:
            color = (200, 200, 200)

          pygame.draw.rect(screen, color, (bx, by, 105, 45), border_radius=8)
          pygame.draw.rect(
              screen, (50, 50, 50), (bx, by, 105, 45), 2, border_radius=8
          )

          txt = font.render(ing, True, (20, 20, 20))
          stock_txt = small_font.render(f"Stock: {stock}", True, (50, 50, 50))
          screen.blit(txt, (bx + 8, by + 6))
          screen.blit(stock_txt, (bx + 8, by + 24))

        # --- 完成した料理の画像（またはプレースホルダー）の表示エリア（ボタンの下に配置） ---
        dish_area_x, dish_area_y = 50, 350
        pygame.draw.rect(
            screen,
            (255, 255, 255),
            (dish_area_x, dish_area_y, 200, 200),
            border_radius=8,
        )
        pygame.draw.rect(
            screen,
            (100, 100, 100),
            (dish_area_x, dish_area_y, 200, 200),
            2,
            border_radius=8,
        )

        if len(active_serving) == 3:
          dish_img = load_dish_image(active_serving)
          if dish_img:
            screen.blit(dish_img, (dish_area_x, dish_area_y))
          else:
            no_img_txt = small_font.render(
                "No Image", True, (150, 100, 100)
            )
            screen.blit(no_img_txt, (dish_area_x + 18, dish_area_y + 42))
        else:
          wait_txt = small_font.render("Select 3", True, (150, 150, 150))
          screen.blit(wait_txt, (dish_area_x + 74, dish_area_y + 92))

        # 総合的なスタート判定
        all_ready = all(
            len(game.customer_servings[o["id"]]) == 3
            for o in game.customer_orders
        )
        total_used = {}
        for c_id, served in game.customer_servings.items():
          for item in served:
            total_used[item] = total_used.get(item, 0) + 1

        stock_shortage = any(
            count > game.inventory[item] for item, count in total_used.items()
        )
        can_start = all_ready and not stock_shortage

        btn_color = (255, 120, 50) if can_start else (180, 180, 180)
        pygame.draw.rect(screen, btn_color, (300, 500, 250, 50), border_radius=10)
        btn_txt = font.render("Start Business!", True, (255, 255, 255))
        screen.blit(btn_txt, (355, 515))

        # 警告文の出し分け
        if not all_ready:
          warn_txt = small_font.render(
              "* Please select 3 ingredients for ALL customers",
              True,
              (200, 50, 50),
          )
          screen.blit(warn_txt, (270, 555))
        elif stock_shortage:
          warn_txt = small_font.render(
              "* Error: Total ingredient usage exceeds current stock!",
              True,
              (200, 50, 50),
          )
          screen.blit(warn_txt, (250, 555))

      elif game.state == "RESULT":
        res_title = title_font.render(
            f"--- Day {game.day} Results & Reviews ---", True, (0, 0, 150)
        )
        screen.blit(res_title, (50, 40))

        rev_txt = font.render(
            f"Revenue: +{game.today_revenue}G | Expenses: Fixed"
            f" {game.today_fixed_cost}G + Random {game.today_random_cost}G ="
            f" -{game.today_total_cost}G",
            True,
            (50, 50, 50),
        )
        screen.blit(rev_txt, (50, 80))

        y_offset = 120
        for report in game.today_reports:
          r_str = (
              f"Customer #{report['id']} | Wants: [{report['wants']}] ->"
              f" Served: [{report['served']}]"
          )
          s_str = f"Score: {report['score']}pt - {report['comment']}"
          t1 = small_font.render(r_str, True, (20, 20, 20))
          t2 = small_font.render(s_str, True, (0, 100, 0))
          screen.blit(t1, (50, y_offset))
          screen.blit(t2, (70, y_offset + 18))
          y_offset += 42

        pygame.draw.rect(
            screen, (50, 150, 255), (300, 520, 250, 50), border_radius=10
        )
        shop_btn_txt = font.render("Go to Shop", True, (255, 255, 255))
        screen.blit(shop_btn_txt, (375, 535))

      elif game.state == "SHOP":
        shop_title = title_font.render(
            "--- Ingredient Shop (1 item = 150G) ---", True, (0, 100, 0)
        )
        screen.blit(shop_title, (50, 40))

        shop_guide = font.render(
            "Click ingredient to buy (+1 stock). Funds available:"
            f" {game.money}G",
            True,
            (50, 50, 50),
        )
        screen.blit(shop_guide, (50, 80))

        for i, ing in enumerate(INGREDIENTS):
          row = 0 if i < 5 else 1
          col = i % 5
          bx = 50 + col * 135
          by = 175 + row * 80

          stock = game.inventory[ing]
          color = (255, 240, 150)

          pygame.draw.rect(screen, color, (bx, by, 120, 45), border_radius=8)
          pygame.draw.rect(
              screen, (50, 50, 50), (bx, by, 120, 45), 2, border_radius=8
          )

          txt = font.render(ing, True, (20, 20, 20))
          stock_txt = small_font.render(
              f"Stock: {stock} (+1)", True, (100, 50, 0)
          )
          screen.blit(txt, (bx + 10, by + 6))
          screen.blit(stock_txt, (bx + 10, by + 24))

        pygame.draw.rect(
            screen, (50, 200, 100), (300, 500, 250, 50), border_radius=10
        )
        next_day_txt = font.render("Next Day", True, (255, 255, 255))
        screen.blit(next_day_txt, (385, 515))

    pygame.display.flip()
    clock.tick(60)
    await asyncio.sleep(0)


if __name__ == "__main__":
  asyncio.run(main())