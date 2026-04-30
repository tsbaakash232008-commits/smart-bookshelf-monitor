import cv2
import numpy as np

# book names mapped to shelf slots
BOOK_NAMES = {
1:"Intro to Astrophysics",
2:"European History Alt 1500-1800",
3:"European History 1500-1800",
4:"Modern Literature",
5:"Global Politics",
6:"Psychology",
7:"Ancient Greece",
8:"Quantum Mechanics",
9:"Philosophy & Ethics",
10:"Medieval Society",
11:"Art History"
}

def detect():

    before = cv2.imread("before.png")
    after = cv2.imread("after.png")

    if before is None or after is None:
        print("Images not found")
        return [],[]

    after = cv2.resize(after,(before.shape[1],before.shape[0]))

    h,w,_ = before.shape

    # crop shelf area
    before = before[int(h*0.35):int(h*0.65),:]
    after  = after[int(h*0.35):int(h*0.65),:]

    gray1 = cv2.cvtColor(before,cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(after,cv2.COLOR_BGR2GRAY)

    slots = 11
    slot_width = w//slots

    removed=[]
    added=[]

    for i in range(slots):

        x1=i*slot_width
        x2=(i+1)*slot_width

        r1 = gray1[:,x1:x2]
        r2 = gray2[:,x1:x2]

        diff = np.mean(cv2.absdiff(r1,r2))

        if diff > 8:

            if np.mean(r1) > np.mean(r2):
                removed.append(i+1)
            else:
                added.append(i+1)

    return removed,added


if __name__=="__main__":

    removed,added = detect()

    print("\nShelf Change Detection")

    if not removed and not added:
        print("No change detected")

    if removed:
        print("\nRemoved Books:")
        for s in removed:
            print("-",BOOK_NAMES.get(s,"Unknown"))

    if added:
        print("\nAdded Books:")
        for s in added:
            print("-",BOOK_NAMES.get(s,"Unknown"))