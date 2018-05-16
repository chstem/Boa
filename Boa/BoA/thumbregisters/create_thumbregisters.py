from __future__ import print_function
import matplotlib
matplotlib.use('pdf')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

### set parameters
mm = 1/25.4     # converts mm to inch

pageheight = 210*mm
pagewidth = 148*mm
xtrim = 0*mm
ytrim = 0*mm

boxwidth = 10*mm
boxsep = 1*mm
textcolor = 'white'
textsize = 14
text_xoffset = 5*mm
boxcolor = (0./255, 55./255, 108./255)      # dark blue
boxcolor = (84./255, 171./255, 63./255)     # GDCh green
categories = ['Greetings', 'Program', 'Talks', 'Poster', 'Index']
boxheights = [42, 41, 41, 41, 41]    # in mm
print('check if this equals the pageheight in mm:', sum(boxheights)+(len(categories)-1)*boxsep/mm)

font = matplotlib.font_manager.FontProperties(family='sans', weight='bold', size=textsize)

### rescale & reverse categories

pageheight += 2*ytrim
pagewidth += 2*xtrim

boxsep = boxsep/pageheight
boxheights = list(map(lambda h:h*mm/pageheight, boxheights[::-1]))

boxwidth = boxwidth/pagewidth
text_xoffset = text_xoffset/pagewidth
categories = categories[::-1]

pagesize = (pagewidth,pageheight)

xtrim = xtrim/pagewidth
ytrim = ytrim/pageheight

### create figures

def make_thumb(side, color, index):

    # color
    if color == 'color':
        bcolor = boxcolor
    elif color == 'black':
        bcolor = 'black'
    else:
        raise ValueError(color)

    # x coordinate + boxw
    if side == 'left':
        angle = -90
        boxx = 0
        textx = text_xoffset + xtrim
    elif side == 'right':
        angle = 90
        boxx = 1 - boxwidth - xtrim
        textx = 1 - text_xoffset - xtrim
    else:
        raise ValueError(side)

    boxw = boxwidth + xtrim

    # y coordinate + height
    boxy = sum(boxheights[:index])+index*boxsep
    boxh = boxheights[index]
    texty = sum(boxheights[:index])+index*boxsep+0.5*boxheights[index]

    if index == 0:
        # first box
        boxh += ytrim
    elif index == len(categories) - 1:
        # last box
        boxh += ytrim

    if index > 0:
        boxy += ytrim

    texty += ytrim

    # add box
    ax.add_patch(matplotlib.patches.Rectangle((boxx,boxy), boxw, boxh, transform=fig.transFigure, fc=bcolor, ec=bcolor, clip_on=False))

    # add text
    ax.text(textx, texty, categories[index], rotation=angle, va='center', ha='center', fontproperties=font, transform=fig.transFigure, color=textcolor)

for side in ('left', 'right',):
    for color in ('color', 'black',):

        # plot all (content)
        fig = plt.figure(figsize=pagesize)
        ax = plt.gca()
        plt.axis('off')

        for i, cat in enumerate(categories):
            make_thumb(side, color, i)

        plt.savefig('Content_%s_%s.pdf' %(side, color))
        plt.close()

        # plot individually
        for i, cat in enumerate(categories):
            fig = plt.figure(figsize=pagesize)
            ax = plt.gca()
            plt.axis('off')
            make_thumb(side, color, i)

            plt.savefig('%s_%s_%s.pdf' %(cat, side, color))
            plt.close()
