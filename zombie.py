from pico2d import *
import random
import math
import game_framework
import game_world
from behavior_tree import BehaviorTree, Action, Sequence, Condition, Selector
import common


# 좀비 이동 관련 상수
PIXEL_PER_METER = (10.0 / 0.3)
RUN_SPEED_KMPH = 10.0
RUN_SPEED_MPM = (RUN_SPEED_KMPH * 1000.0 / 60.0)
RUN_SPEED_MPS = (RUN_SPEED_MPM / 60.0)
RUN_SPEED_PPS = (RUN_SPEED_MPS * PIXEL_PER_METER)

# 애니메이션
TIME_PER_ACTION = 0.5
ACTION_PER_TIME = 1.0 / TIME_PER_ACTION
FRAMES_PER_ACTION = 10.0

animation_names = ['Walk', 'Idle']


class Zombie:

    images = None


    def load_images(self):
        if Zombie.images is None:
            Zombie.images = {}
            for name in animation_names:
                Zombie.images[name] = [
                    load_image("./zombie/" + name + f" ({i}).png") for i in range(1, 11)
                ]
            Zombie.font = load_font('ENCR10B.TTF', 40)
            Zombie.marker_image = load_image('hand_arrow.png')

    # 초기화
    def __init__(self, x=None, y=None):
        self.x = x if x else random.randint(100, 1180)
        self.y = y if y else random.randint(100, 924)
        self.load_images()

        self.dir = 0.0
        self.speed = 0.0
        self.frame = random.randint(0, 9)
        self.state = 'Idle'

        self.ball_count = 0  # 좀비가 먹은 공 개수

        # 현재 목표 위치
        self.tx, self.ty = 1000, 1000

        # 순찰 경로
        self.patrol_points = [
            (43, 274), (1118, 274), (1050, 494), (575, 804),
            (235, 991), (575, 804), (1050, 494), (1118, 274)
        ]
        self.patrol_index = 0

        self.build_behavior_tree()

    # 충돌 박스
    def get_bb(self):
        return self.x - 50, self.y - 50, self.x + 50, self.y + 50

    # 매프레임 업데이트
    def update(self):
        self.frame = (self.frame +
                      FRAMES_PER_ACTION * ACTION_PER_TIME * game_framework.frame_time) % FRAMES_PER_ACTION

        self.bt.run()

    # 화면 그리기
    def draw(self):
        # 방향 반전
        if math.cos(self.dir) < 0:
            Zombie.images[self.state][int(self.frame)].composite_draw(
                0, 'h', self.x, self.y, 100, 100)
        else:
            Zombie.images[self.state][int(self.frame)].draw(self.x, self.y, 100, 100)

        Zombie.font.draw(self.x - 10, self.y + 60, f'{self.ball_count}', (0, 0, 255))
        Zombie.marker_image.draw(self.tx + 25, self.ty - 25)

        draw_rectangle(*self.get_bb())
        draw_circle(self.x, self.y, int(PIXEL_PER_METER * 7), 0, 255, 0)

    def handle_event(self, event):
        pass

    # 충돌 처리 (공과 충돌하면 공 개수 증가)
    def handle_collision(self, group, other):
        if group == 'zombie:ball':
            self.ball_count += 1

    # 목표 위치 설정
    def set_target_location(self, x=None, y=None):
        self.tx, self.ty = x, y
        return BehaviorTree.SUCCESS

    # 거리 비교 (제곱 활용)
    def distance_less_than(self, x1, y1, x2, y2, r):
        distance2 = (x2 - x1) ** 2 + (y2 - y1) ** 2
        return distance2 < (r * PIXEL_PER_METER) ** 2

    # 목표 방향으로 조금씩 이동
    def move_little_to(self, tx, ty):
        self.dir = math.atan2(ty - self.y, tx - self.x)
        distance = RUN_SPEED_PPS * game_framework.frame_time
        self.x += distance * math.cos(self.dir)
        self.y += distance * math.sin(self.dir)

    # 목표 위치로 이동
    def move_to(self, r=0.5):
        self.state = 'Walk'

        self.dir = math.atan2(self.ty - self.y, self.tx - self.x)
        distance = RUN_SPEED_PPS * game_framework.frame_time
        self.x += distance * math.cos(self.dir)
        self.y += distance * math.sin(self.dir)

        if self.distance_less_than(self.x, self.y, self.tx, self.ty, r):
            return BehaviorTree.SUCCESS
        return BehaviorTree.RUNNING

    # 랜덤 위치 선택
    def set_random_location(self):
        self.tx = random.randint(100, 1180)
        self.ty = random.randint(100, 924)
        return BehaviorTree.SUCCESS

    # 소년이 가까이 있는가?
    def if_boy_nearby(self, distance):
        if self.distance_less_than(self.x, self.y, common.boy.x, common.boy.y, distance):
            return BehaviorTree.SUCCESS
        return BehaviorTree.FAIL


    def zombie_has_more_balls(self):
        return BehaviorTree.SUCCESS if self.ball_count >= common.boy.ball_count else BehaviorTree.FAIL

    def zombie_has_less_balls(self):
        return BehaviorTree.SUCCESS if self.ball_count < common.boy.ball_count else BehaviorTree.FAIL


    def move_to_boy(self, r=0.5):
        self.state = 'Walk'
        self.move_little_to(common.boy.x, common.boy.y)

        if self.distance_less_than(self.x, self.y, common.boy.x, common.boy.y, r):
            return BehaviorTree.SUCCESS
        return BehaviorTree.RUNNING


    def flee_from_boy(self):
        self.state = 'Walk'
        bx, by = common.boy.x, common.boy.y


        self.dir = math.atan2(self.y - by, self.x - bx)
        distance = RUN_SPEED_PPS * game_framework.frame_time
        self.x += math.cos(self.dir) * distance
        self.y += math.sin(self.dir) * distance

        return BehaviorTree.RUNNING


    def next_patrol_pos(self):
        x, y = self.patrol_points[self.patrol_index]
        self.patrol_index = (self.patrol_index + 1) % len(self.patrol_points)
        self.tx, self.ty = x, y
        return BehaviorTree.SUCCESS


    def build_behavior_tree(self):


        wander = Sequence('배회',
                          Action('랜덤 위치 설정', self.set_random_location),
                          Action('랜덤 위치로 이동', self.move_to))


        cond_boy_near = Condition('소년이 7m 안인가?', self.if_boy_nearby, 7)

        # 추적
        chase = Sequence('추적',
                         Condition('좀비 공 >= 소년 공?', self.zombie_has_more_balls),
                         Action('소년에게 이동', self.move_to_boy))


        flee = Sequence('도망',
                        Condition('좀비 공 < 소년 공?', self.zombie_has_less_balls),
                        Action('소년에게서 도망', self.flee_from_boy))

        # 소년이 가까우면 → 추적 or 도망
        boy_react = Sequence('소년 반응',
                             cond_boy_near,
                             Selector('추적 or 도망', chase, flee))


        root = Selector('최종 선택', boy_react, wander)

        self.bt = BehaviorTree(root)
