"""
Hand rig for Maya.
Jeremy Estrada December 2011
This set up assumes a relatively simple, standard hand skeleton has been constructed.
Select the root joint of the hand skeleton, instantiate the handRig object,
then run it's "rigHand" method.

---------|
EXAMPLE: |
---------|
import handRig
import maya.cmds as mc

sObj = mc.ls(sl=True)
oRig = handRig.handRig(sObj)
oRig.rigHand()

"""
import maya.cmds as mc
import maya.OpenMaya as om
import re

class handRig(object):

    def __init__(self, sControl = ""):
        "Get important info and store it in class scope variables."

        if sControl == "":
            try:
                sControl = [x for x in mc.ls(sl=True) if re.search("(transform|joint)", mc.nodeType(x))][0]
            except TypeError:
                mc.warning("Select a valid control object")
                return False

        self.control = sControl
        fWorldX = mc.xform(sControl, q=True, ws=True, a=True, t=True)[0]
        if fWorldX > 0:
            self.side = "left"
        else:
            self.side = "right"

        self.names = []
        self.topJoint = self.getTopJoint()
        self.fingers = self.getFingers() #returns a dictionary

    def rigHand(self):
        "This is the main function."

        #add some attrs
        listAttrs = ["Spread", "Twist", "Stretch", "Cup"]
        for sAttr in listAttrs:
            for sName in self.names:
                if sAttr == "Stretch": fDv = 1.0
                else: fDv = 0.0
                sAttrName = self.side+sName.capitalize()+sAttr
                mc.addAttr(self.control, ln=sAttrName, k=True, h=False, dv=fDv)
        
        for sName in self.names:
            listJnts = self.fingers[sName]
            #find out if the finger has a metacarpal joint
            nNumJnts = len(listJnts)
            if sName == "thumb":
                if nNumJnts >=4: bMeta = True
                else: bMeta = False
                listNames = ["meta", "base", "mid", "end"]
                    
            else:
                if nNumJnts >= 5: bMeta = True
                else: bMeta = False
                listNames = ["meta", "base", "mid", "tip", "end"]
                
            #name joints properly                                
            if bMeta: pass
            else: listNames.remove("meta")
            for i, sPart in zip(range(nNumJnts), listNames):
                sNewName = self.side+"_"+sName+sPart.capitalize()+"_jnt"
                mc.rename(listJnts[i], sNewName)
                listJnts.pop(i)
                listJnts.insert(i, sNewName)
                #add the attrs for this finger
                if re.search("(meta|end)", sPart):
                    pass
                else:
                    sAttr = self.side+sName.capitalize()+sPart.capitalize()
                    mc.addAttr(self.control, ln=sAttr, k=True, h=False)
                if bMeta and sName == "thumb" and sPart == "meta":
                    mc.addAttr(self.control, ln=self.side+sName.capitalize()+"Meta", k=True, h=False)
                    
                #orient the joints properly                    
                if sPart == "end":
                    mc.setAttr(listJnts[i]+".jointOrient", 0,0,0)
                else:
                    sUpVec = mc.group(n="upVecTemp", em=True)
                    sUpVecGrp = mc.group(n="upVecTempGrp", em=True)
                    mc.parent(sUpVec, sUpVecGrp)
                    if bMeta: sMatch = "meta"
                    else: sMatch = "base"
                    if sPart == sMatch:
                        mc.delete(mc.parentConstraint(self.control, sUpVecGrp))
                    else:
                        sParent = mc.listRelatives(listJnts[i], p=True)[0]
                        mc.delete(mc.parentConstraint(sParent, sUpVecGrp))
                    sChld = mc.listRelatives(listJnts[i])[0]
                    mc.parent(sChld, w=True)                    
                    mc.setAttr(sUpVec+".ty", 20)
                    mc.delete(mc.pointConstraint(listJnts[i], sUpVecGrp))
                    mc.delete(
                        mc.aimConstraint(
                            sChld,
                            listJnts[i],
                            upVector=[0,1,0],
                            aimVector=[1,0,0],
                            worldUpType="object",
                            worldUpObject=sUpVec))
                    self.orientFromRotation(listJnts[i])
                    if sName == "thumb" and sPart == sMatch:
                        if self.side == "left":
                            mc.setAttr(listJnts[i]+".rx", 45)
                        else:
                            mc.setAttr(listJnts[i]+".rx", -45)
                        self.orientFromRotation(listJnts[i])                        
                    mc.parent(sChld, listJnts[i])
                    mc.delete(sUpVecGrp)

                #hook up control attrs to joint rotations
                if re.search("end", sPart):
                    pass
                else:
                    if bMeta and sPart == "meta" and sName != "thumb":                        
                        sMult = mc.createNode("multDoubleLinear", n=self.side+sName.capitalize()+"_multDoubleLinear")
                        nNmIdx = self.names.index(sName)
                        nNumNames = len(self.names)
                        fVal = float(nNmIdx)/float(nNumNames)
                        mc.setAttr(sMult+".input1", fVal)
                        mc.connectAttr(
                            self.control+"."+self.side+sName.capitalize()+"Cup",
                            sMult+".input2")
                        mc.connectAttr(sMult+".output", listJnts[i]+".rz")
                    else:
                        if not bMeta:
                            try:
                                mc.deleteAttr(self.control, attribute=self.side+sName.capitalize()+"Cup")
                            except RuntimeError:
                                pass
                        mc.connectAttr(self.control+"."+self.side+sName.capitalize()+sPart.capitalize(), listJnts[i]+".rz")
                        mc.connectAttr(self.control+"."+self.side+sName.capitalize()+"Stretch", listJnts[i]+".sx")
                        if sPart == "base" and sName != "thumb":
                            mc.connectAttr(
                                self.control+"."+self.side+sName.capitalize()+"Spread",
                                listJnts[i]+".ry")
                            mc.connectAttr(
                                self.control+"."+self.side+sName.capitalize()+"Twist",
                                listJnts[i]+".rx")
                        if sName == "thumb" and sPart == "meta":
                            mc.connectAttr(
                                self.control+"."+self.side+sName.capitalize()+"Spread",
                                listJnts[i]+".ry")
                            mc.connectAttr(
                                self.control+"."+self.side+sName.capitalize()+"Twist",
                                listJnts[i]+".rx")
        return

    def getFingers(self):
        "Find out how many fingers this hand skeleton has and assign names."

        """
        dictFingers = {
            "index":["joint1", "joint2", etc],
            "middle":["joint1", "joint2",etc],
            "etc":[etc]
            }
        """
        #get the children of the top joint
        #these are the joints for each finger
        #the number of children will help determine how to name them
        #once you figure out which one is the thumb, you'll know how to name them
        #the thumb is the shortest one!
        listChildJoints = [x for x in mc.listRelatives(self.topJoint) if mc.nodeType(x)=="joint"]
        listJntChains = []
        
        for sJnt in listChildJoints:
            listChain = [x for x in mc.listRelatives(sJnt, ad=True) if mc.nodeType(x)=="joint"]
            listChain.append(sJnt)
            listChain.reverse()
            listJntChains.append(listChain)

        #now find which chain is the shortest. This one is the thumb!
        nNumChains = len(listJntChains)
        fShortest = 999999999999999999.9 #no chain is longer than this
        for i in range(nNumChains):
            sBaseJnt = listJntChains[i][0]
            fLength = self.getLength(sBaseJnt, 0.0)
            if fLength < fShortest:
                fShortest = fLength
                nChnIdx = i

        sThumbBase = listJntChains[nChnIdx][0]
        listThumbJnts = listJntChains.pop(nChnIdx)
        #now find which of the remaining base joints is closest to the thumb base
        #this one is the index finger!
        #now find which of the remaining base joints is closest to the index. This is the next one!
        #continue til you run out of fingers
        listEmpty = []
        listOrdered = self.orderFingers(sThumbBase, listJntChains, listEmpty)
        nNumFngrs = len(listOrdered)
        if nNumFngrs == 4:
            self.names = ["index", "middle", "ring", "pinky", "thumb"]
        elif nNumFngrs == 3:
            self.names = ["index", "middle", "pinky", "thumb"]
        else:
            for i in range(nNumFngrs):
                if i == 0: self.names.append("index")
                elif i == (nNumFngrs-1): self.names.append("pinky")
                else: self.names.append("finger0"+str(i+1))

        dictFingers = {}
        dictFingers["thumb"] = listThumbJnts
        for i in range(nNumFngrs):
            dictFingers[self.names[i]] = listOrdered[i]
        
        return dictFingers

    def getTopJoint(self):
        "Find the joint that is being driven by the wrist control."

        #what joint is constrained to the wrist control?
        try:
            sConst = mc.listConnections(self.control, s=False, d=True, type="constraint")[0]
        except TypeError, e:
            mc.warning("Can't find hand connected to control node!")
            raise e
            
        sTopJoint = mc.listConnections(sConst, s=False, d=True)[0]

        return sTopJoint

    def getLength(self, sJoint, fInit):
        "Get the length of the joint chain passed in."

        try:
            if fInit == 0.0:
                sChldJnt = sJoint
                sJoint = self.topJoint
            else:
                sChldJnt = mc.listRelatives(sJoint)[0]
            listBaseTrns = mc.xform(sJoint, q=True, ws=True, a=True, t=True)
            listTrns = mc.xform(sChldJnt, q=True, ws=True, a=True, t=True)
            oVec = om.MVector(
                listTrns[0]-listBaseTrns[0],
                listTrns[1]-listBaseTrns[1],
                listTrns[2]-listBaseTrns[2])
            fLength = oVec.length()            
            fLength += fInit
            return self.getLength(sChldJnt, fLength)
        except TypeError:
            return fInit

    def orderFingers(self, sBase, listJntChains, listOrderedChains=[]):
        "Place these chains in order from index to pinky."

        nNumChains = len(listJntChains)
        fShortest = 99999999999999999999
        for i in range(nNumChains):
            sJnt = listJntChains[i][0]
            listTrans = mc.xform(sJnt, q=True, ws=True, a=True, t=True)
            listBaseTrans = mc.xform(sBase, q=True, ws=True, a=True, t=True)
            oPnt = om.MPoint(listTrans[0], listTrans[1], listTrans[2])
            oBasePnt = om.MPoint(listBaseTrans[0], listBaseTrans[1], listBaseTrans[2])
            fDist = oPnt.distanceTo(oBasePnt)
            if fDist < fShortest:
                fShortest = fDist
                nIdx = i
                sNewBase = sJnt
        
        listNextFngr = listJntChains.pop(nIdx)
        listOrderedChains.append(listNextFngr)
        if len(listJntChains) == 0:
            return listOrderedChains
        else:
            return self.orderFingers(sNewBase, listJntChains, listOrderedChains)

    def orientFromRotation(self, sJnt):
        "Set the given joint's jointOrients from its current world space orientation."

        sTmp = mc.group(n="tempOrienter", em=True)
        mc.delete(mc.parentConstraint(sJnt, sTmp))
        mc.setAttr(sJnt+".jointOrient", 0,0,0)
        mc.delete(mc.orientConstraint(sTmp, sJnt))
        listRot = mc.xform(sJnt, q=True, os=True, ro=True)
        mc.setAttr(sJnt+".jointOrient", listRot[0], listRot[1], listRot[2])
        mc.setAttr(sJnt+".r", 0,0,0)
        mc.delete(sTmp)
