# -*- coding: utf-8 -*-


from sys import stderr
import numpy as np


BSIZE = 9  # board size
EBSIZE = BSIZE + 2  # extended board size
BVCNT = BSIZE ** 2  # vertex count
EBVCNT = EBSIZE ** 2  # extended vertex count

# 两个越界的位置规定为PASS-81和unvaild-82
# pass
PASS = EBVCNT
# invalid position
VNULL = EBVCNT + 1
# 贴目
KOMI = 7.0
# v的(右下左上)四个位置
dir4 = [1, EBSIZE, -1, -EBSIZE]
# v的(四个角)位置
diag4 = [1 + EBSIZE, EBSIZE - 1, -EBSIZE - 1, 1 - EBSIZE]

KEEP_PREV_CNT = 2
#12当前黑白棋
#3456前两次黑白棋
#7当前棋色
FEATURE_CNT = KEEP_PREV_CNT * 2 + 3  # 7

x_labels = "ABCDEFGHJKLMNOPQRST"


def ev2xy(ev):
    '''
    e.g.ev=12==>（1,1）;
    ev=13==>(2,1)
    从行到列→↓
    :param ev:
    :return:
    '''
    return ev % EBSIZE, ev // EBSIZE


def xy2ev(x, y):
    '''
    将坐标转换成向量
    :param x:
    :param y:
    :return:
    '''
    return y * EBSIZE + x


def rv2ev(rv):
    '''
    更新坐标索引起点=>0-8向量转化为1-9向量
    12 - 108
    :param rv: 
    :return: 
    '''
    if rv == BVCNT:
        return PASS
    return rv % BSIZE + 1 + (rv // BSIZE + 1) * EBSIZE


def ev2rv(ev):
    '''
    将棋盘1-9向量==>0-8向量
    :param ev:
    :return:
    '''
    if ev == PASS:
        return BVCNT
    return ev % EBSIZE - 1 + (ev // EBSIZE - 1) * BSIZE


def ev2str(ev):
    '''
    将下棋位置转化为str
    :param ev:
    :return:
    '''
    if ev >= PASS:
        return "pass"
    x, y = ev2xy(ev)
    return x_labels[x - 1] + str(y)


def str2ev(v_str):
    '''
    字符形式信息转换为ev
    :param v_str:
    :return:
    '''
    v_str = v_str.upper()
    if v_str == "PASS" or v_str == "RESIGN":    # 放弃
        return PASS
    else:
        x = x_labels.find(v_str[0]) + 1
        y = int(v_str[1:])
        return xy2ev(x, y)


rv_list = [rv2ev(i) for i in range(BVCNT)]

#并查集？
class StoneGroup(object):

    def __init__(self):
        self.lib_cnt = VNULL  # liberty count(气的数目)
        self.size = VNULL  # stone size(该气的大小_包含棋子数)
        self.v_atr = VNULL  # liberty position if in Atari(在叫吃情况下的气)
        self.libs = set()  # set of liberty positions(气集合)

    def clear(self, stone=True):
        # clear as placed stone or empty
        self.lib_cnt = 0 if stone else VNULL
        self.size = 1 if stone else VNULL
        self.v_atr = VNULL
        self.libs.clear()

    def add(self, v):
        # add liberty at v
        if v not in self.libs:
            self.libs.add(v)
            self.lib_cnt += 1
            self.v_atr = v

    def sub(self, v):
        # remove liberty at v
        if v in self.libs:
            self.libs.remove(v)
            self.lib_cnt -= 1

    def merge(self, other):
        # merge with aother stone group
        self.libs |= other.libs
        self.lib_cnt = len(self.libs)
        self.size += other.size
        if self.lib_cnt == 1:
            for lib in self.libs:
                self.v_atr = lib

#棋盘
class Board(object):
    '''
    记录比赛信息的量
    注意: 没有全局变量记录当前局自己的颜色
    '''
    def __init__(self):
        # 1-d array ([EBVCNT]) of stones or empty or exterior
        # 一维阵列([EBVCNT])的棋色、空、边界
        # 0: white 1: black
        # 2: empty 3: exterior(越界、边界)
        self.color = np.full(EBVCNT, 3)
        self.sg = [StoneGroup() for _ in range(EBVCNT)]  # stone groups
        self.clear()

    def clear(self):
        self.color[rv_list] = 2  # 将能下子的地方标记为空
        self.id = np.arange(EBVCNT)  # id of stone group
        self.next = np.arange(EBVCNT)  # next position in the same group
        for i in range(EBVCNT):
            self.sg[i].clear(stone=False)
        self.prev_color = [np.copy(self.color) for _ in range(KEEP_PREV_CNT)]

        self.ko = VNULL  # illegal position due to Ko(劫)
        self.turn = 1  # black first
        self.move_cnt = 0  # move count
        self.prev_move = VNULL  # previous move
        self.remove_cnt = 0  # removed stones count(移掉子的数目)
        self.history = []   # 该局历史

    def copy(self, b_cpy):
        '''
        实现对象的拷贝功能
        :param b_cpy: Board对象
        :return:
        '''
        b_cpy.color = np.copy(self.color)
        b_cpy.id = np.copy(self.id)
        b_cpy.next = np.copy(self.next)
        for i in range(EBVCNT):
            b_cpy.sg[i].lib_cnt = self.sg[i].lib_cnt
            b_cpy.sg[i].size = self.sg[i].size
            b_cpy.sg[i].v_atr = self.sg[i].v_atr
            b_cpy.sg[i].libs |= self.sg[i].libs
        for i in range(KEEP_PREV_CNT):
            b_cpy.prev_color[i] = np.copy(self.prev_color[i])

        b_cpy.ko = self.ko
        b_cpy.turn = self.turn
        b_cpy.move_cnt = self.move_cnt
        b_cpy.prev_move = self.prev_move
        b_cpy.remove_cnt = self.remove_cnt

        for h in self.history:
            b_cpy.history.append(h)

    def remove(self, v):
        # remove stone group including stone at v
        '''
        提子操作
        :param v:
        :return:
        '''
        v_tmp = v
        while 1:
            self.remove_cnt += 1
            self.color[v_tmp] = 2  # empty
            self.id[v_tmp] = v_tmp  # reset id
            for d in dir4:
                nv = v_tmp + d
                # add liberty to neighbor groups
                self.sg[self.id[nv]].add(v_tmp)
            v_next = self.next[v_tmp]
            self.next[v_tmp] = v_tmp
            v_tmp = v_next
            if v_tmp == v:
                break  # finish when all stones are removed

    def merge(self, v1, v2):
        # merge stone groups at v1 and v2
        '''
        并查集，将两个group合并
        :param v1:
        :param v2:
        :return:
        '''
        id_base = self.id[v1]
        id_add = self.id[v2]
        if self.sg[id_base].size < self.sg[id_add].size:
            id_base, id_add = id_add, id_base  # swap
        self.sg[id_base].merge(self.sg[id_add])

        v_tmp = id_add
        while 1:
            self.id[v_tmp] = id_base  # change id to id_base
            v_tmp = self.next[v_tmp]
            if v_tmp == id_add:
                break
        # swap next id for circulation
        self.next[v1], self.next[v2] = self.next[v2], self.next[v1]

    def place_stone(self, v):
        '''
        落子
        :param v: 位置0-120的一个点
        :return:
        '''
        self.color[v] = self.turn
        self.id[v] = v
        self.sg[self.id[v]].clear(stone=True)
        for d in dir4:
            nv = v + d
            if self.color[nv] == 2:
                self.sg[self.id[v]].add(nv)  # add liberty
            else:
                self.sg[self.id[nv]].sub(v)  # remove liberty
        # merge stone groups
        for d in dir4:
            nv = v + d
            if self.color[nv] == self.turn and self.id[nv] != self.id[v]:
                self.merge(v, nv)
        # remove opponent's stones
        self.remove_cnt = 0
        for d in dir4:
            nv = v + d
            if self.color[nv] == int(self.turn == 0) and \
                    self.sg[self.id[nv]].lib_cnt == 0:
                self.remove(nv)

    def legal(self, v):
        '''
        判断当前落子点是否合法
        :param v:
        :return:
        '''
        # pass为合法
        if v == PASS:
            return True
        # 如果不能空,则false
        elif v == self.ko or self.color[v] != 2:
            return False

        stone_cnt = [0, 0]
        atr_cnt = [0, 0]
        for d in dir4:  # [1, EBSIZE, -1, -EBSIZE]
            nv = v + d
            c = self.color[nv]
            # 如果有任意一个方向空.即不是眼,那么就可以下
            if c == 2:
                return True
            # 计算是否为眼
            elif c <= 1:
                stone_cnt[c] += 1
                if self.sg[self.id[nv]].lib_cnt == 1:
                    atr_cnt[c] += 1

        return (atr_cnt[int(self.turn == 0)] != 0 or
                atr_cnt[self.turn] < stone_cnt[self.turn])

    def eyeshape(self, v, pl):
        '''
        当前这步能否形成眼
        :param v: 位置
        :param pl: self.turn,当前player的颜色
        # int(pl == 0) 判断是否为pl相对颜色:如果传1黑,那么就是0白.
        :return:
        '''
        # 如果pass那么一定不能构成眼
        if v == PASS:
            return False

        for d in dir4:      # [1, EBSIZE, -1, -EBSIZE]
            c = self.color[v + d]
            # 一旦有位置是空的or,那么没有形成眼
            if c == 2 or c == int(pl == 0):
                return False

        diag_cnt = [0, 0, 0, 0]
        for d in diag4:  # [1 + EBSIZE, EBSIZE - 1, -EBSIZE - 1, 1 - EBSIZE]
            nv = v + d
            diag_cnt[self.color[nv]] += 1

        wedge_cnt = diag_cnt[int(pl == 0)] + int(diag_cnt[3] > 0)
        if wedge_cnt == 2:
            for d in diag4:  # [1 + EBSIZE, EBSIZE - 1, -EBSIZE - 1, 1 - EBSIZE]
                nv = v + d
                if self.color[nv] == int(pl == 0) and \
                        self.sg[self.id[nv]].lib_cnt == 1 and \
                        self.sg[self.id[nv]].v_atr != self.ko:
                    return True

        return wedge_cnt < 2

    def play(self, v, not_fill_eye=True):
        '''
        走子
        :param v: 位置
        :param not_fill_eye: 是否不填眼
        :return:
        '''
        if not self.legal(v):
            return 1
        elif not_fill_eye and self.eyeshape(v, self.turn):
            return 2
        # 如果能走，且满足眼的要求
        else:
            for i in range(KEEP_PREV_CNT - 1)[::-1]:
                self.prev_color[i + 1] = np.copy(self.prev_color[i])
            self.prev_color[0] = np.copy(self.color)

            if v == PASS:
                self.ko = VNULL
            else:
                self.place_stone(v)
                id = self.id[v]
                self.ko = VNULL
                if self.remove_cnt == 1 and \
                        self.sg[id].lib_cnt == 1 and \
                        self.sg[id].size == 1:
                    self.ko = self.sg[id].v_atr

        # 一方下完后进行记录,并切换下子方
        self.prev_move = v
        self.history.append(v)
        self.turn = int(self.turn == 0) # 实际是一个取反的作用
        self.move_cnt += 1

        return 0

    def random_play(self):
        '''
        随机往空的位置下棋
        :return: v: int
        '''
        empty_list = np.where(self.color == 2)[0]
        np.random.shuffle(empty_list)

        # 如果有子可以下
        for v in empty_list:
            if self.play(v, True) == 0:
                return v

        # 没子可下,那么PASS
        self.play(PASS)
        return PASS

    def score(self):
        '''
        计算得分
        :return: int
        '''
        stone_cnt = [0, 0]
        for rv in range(BVCNT):
            v = rv2ev(rv)
            c = self.color[v]
            if c <= 1:
                stone_cnt[c] += 1
            else:
                nbr_cnt = [0, 0, 0, 0]
                for d in dir4:
                    nbr_cnt[self.color[v + d]] += 1
                if nbr_cnt[0] > 0 and nbr_cnt[1] == 0:
                    stone_cnt[0] += 1
                elif nbr_cnt[1] > 0 and nbr_cnt[0] == 0:
                    stone_cnt[1] += 1
        return stone_cnt[1] - stone_cnt[0] - KOMI

    def rollout(self, show_board=False):
        '''
        模拟随机
        :param show_board: 是否显示棋盘
        :return:
        '''
        while self.move_cnt < EBVCNT * 2:
            prev_move = self.prev_move
            move = self.random_play()
            if show_board and move != PASS:
                stderr.write("\nmove count=%d\n" % self.move_cnt)
                self.showboard()
            # 当局游戏结束的条件
            if prev_move == PASS and move == PASS:
                break

    def showboard(self):
        '''
        输出当前的棋盘
        :return:
        '''

        def print_xlabel():
            line_str = "  "
            for x in range(BSIZE):
                line_str += " " + x_labels[x] + " "
            stderr.write(line_str + "\n")

        print_xlabel()

        for y in range(1, BSIZE + 1)[::-1]:  # 9, 8, ..., 1
            line_str = str(y) if y >= 10 else " " + str(y)
            for x in range(1, BSIZE + 1):
                v = xy2ev(x, y)
                x_str = " . "
                color = self.color[v]
                if color <= 1:
                    stone_str = "O" if color == 0 else "X"
                    if v == self.prev_move:
                        x_str = "[" + stone_str + "]"
                    else:
                        x_str = " " + stone_str + " "
                line_str += x_str
            line_str += str(y) if y >= 10 else " " + str(y)
            stderr.write(line_str + "\n")

        print_xlabel()
        stderr.write("\n")

    def feature(self):
        '''
        提取棋盘特征，记忆上一次，上上次的棋路
        :return:
        '''
        feature_ = np.zeros((EBVCNT, FEATURE_CNT), dtype=np.float)
        my = self.turn
        opp = int(self.turn == 0)

        feature_[:, 0] = (self.color == my)
        feature_[:, 1] = (self.color == opp)
        for i in range(KEEP_PREV_CNT):
            feature_[:, (i + 1) * 2] = (self.prev_color[i] == my)
            feature_[:, (i + 1) * 2 + 1] = (self.prev_color[i] == opp)
        feature_[:, FEATURE_CNT - 1] = my

        return feature_[rv_list, :]


    def hash(self):
        '''
        哈希算状态
        :return:
        '''
        return (hash(self.color.tostring()) ^
                hash(self.prev_color[0].tostring()) ^ self.turn)


    def info(self):
        empty_list = np.where(self.color == 2)[0]
        cand_list = []
        #找到合法且不是眼的坐标（所有可行点）
        for v in empty_list:
            if self.legal(v) and not self.eyeshape(v, self.turn):
                cand_list.append(ev2rv(v))
        cand_list.append(ev2rv(PASS))
        #当前状态，走子数，输出决策
        return (self.hash(), self.move_cnt, cand_list)
