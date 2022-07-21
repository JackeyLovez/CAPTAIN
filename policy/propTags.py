from ctypes import c_bool
from graph.Subject import Subject
from graph.Object import Object
from policy.floatTags import TRUSTED, UNTRUSTED, BENIGN, PUBLIC
from policy.floatTags import isTRUSTED, isUNTRUSTED
from policy.floatTags import citag, ctag, itag, etag, isRoot
from parse.eventType import EXECVE_SET, SET_UID_SET, lttng_events, cdm_events, standard_events
from parse.eventType import READ_SET, LOAD_SET, EXECVE_SET, WRITE_SET, INJECT_SET, CREATE_SET, CLONE_SET, UPDATE_SET

def propTags_pre():
   pass

def propTags(event, s, o, whitelisted = False, att = 0.2, decay = 16, format = 'cdm', morse = None):
   if citag(o.tags()) != 1.0 and (cdm_events[event['type']] in LOAD_SET or cdm_events[event['type']] in EXECVE_SET): 
      a = 0
   target_event_id = '5A5D146A-C259-9DE3-6A4E-7AA84EAE7B92'
   if event['uuid'] == target_event_id:
      a = 0

   target_node_id = '25237608-007E-5B93-2EB0-08F80F349FC6'
   if s.id == target_node_id or o.id == target_node_id:
      if s.id == target_node_id:
         if s.iTag != 1.0:
            a = 0
      if o.id == target_node_id:
         if o.iTag != 1.0:
            a = 0

   if format == 'cdm':
      event_type = cdm_events[event['type']]
   elif format == 'lttng':
      event_type = lttng_events[event['type']]

   intags = None
   newtags = None
   whitelisted = False
   ab = att
   ae = att/2
   dpPow = decay
   dpi = 1.0/pow(2, dpPow)
   dpc = 1.0/pow(2, dpPow)

   if event_type in LOAD_SET or event_type in EXECVE_SET or event_type in READ_SET:
      intags = o.tags()
      
   if event_type in READ_SET:
      assert isinstance(s,Subject) and isinstance(o,Object)
      stg = s.tags()
      it = itag(stg)
      oit = itag(intags)
      ct = ctag(stg)
      oct = ctag(intags)
      
      citag_grad, etag_grad, itag_grad, ctag_grad = s.get_grad()
      ci_init_id, e_init_id, i_init_id, c_init_id = s.getInitID()

      if it > oit:
         itag_grad = o.get_itag_grad()
         i_init_id = o.getiTagInitID()
         it = min(it, oit)

      if ct > oct:
         ctag_grad = o.get_ctag_grad()
         c_init_id = o.getcTagInitID()
         ct = min(ct, oct)
      s.setSubjTags([citag(stg), etag(stg), it, ct])
      s.set_grad([citag_grad, etag_grad, itag_grad, ctag_grad])
      s.setInitID([ci_init_id, e_init_id, i_init_id, c_init_id])

   elif event_type in LOAD_SET:
      if o.isFile():
         a = citag(o.tags())
         if citag(o.tags()) != 1.0: 
            a = 0
         stg = s.tags()
         citag_grad, etag_grad, itag_grad, ctag_grad = s.get_grad()
         ci_init_id, e_init_id, i_init_id, c_init_id = s.getInitID()

         if citag(stg) > citag(intags):
            citag_grad = o.get_citag_grad()
            ci_init_id = o.getciTagInitID()
         cit = min(citag(stg), citag(intags))

         # et = etag(stg)
         # if (et > cit):
         #    et = cit
         #    etag_grad = citag_grad
         #    e_init_id = ci_init_id
         #    # s.seteTagInitID(s.getciTagInitID())

         if itag(stg) > itag(intags):
            itag_grad = o.get_itag_grad()
            i_init_id = o.getiTagInitID()
         it = min(itag(stg), itag(intags))

         if ctag(stg) > ctag(intags):
            ctag_grad = o.get_ctag_grad()
            c_init_id = o.getcTagInitID()
         ct = min(ctag(stg), ctag(intags))

         # ct = ctag(stg)

         s.setSubjTags([cit, etag(stg), it, ct])
         s.set_grad([citag_grad, etag_grad, itag_grad, ctag_grad])
         s.setInitID([ci_init_id, e_init_id, i_init_id, c_init_id])

   elif event_type in INJECT_SET:
      assert isinstance(o,Subject)
      intags = s.tags()
      stg = o.tags()

      # citag_grad = s.get_citag_grad()
      # etag_grad = o.get_etag_grad()
      # invtag_grad = o.get_invtag_grad()
      # itag_grad = s.get_itag_grad()
      # ctag_grad = s.get_ctag_grad()

      citag_grad, etag_grad, invtag_grad, itag_grad, ctag_grad = o.get_grad()
      ci_init_id, e_init_id, inv_init_id, i_init_id, c_init_id = o.getInitID()

      if citag(stg) > citag(intags):
         citag_grad = s.get_citag_grad()
         ci_init_id = s.getciTagInitID()
      cit = min(citag(stg), citag(intags))

      if (isTRUSTED(cit) and itag(intags) < 0.5):
         cit = UNTRUSTED
         citag_grad = s.get_itag_grad()
         ci_init_id = s.getiTagInitID()

      et = etag(stg)
      if (et > cit):
         et = cit
         etag_grad = citag_grad
         e_init_id = ci_init_id

      inv = invtag(stg)
      if (isUNTRUSTED(cit)):
         inv = UNTRUSTED
         invtag_grad = citag_grad
         inv_init_id = ci_init_id

      if itag(stg) > itag(intags):
         itag_grad = s.get_itag_grad()
         i_init_id = s.getiTagInitID()
      it = min(itag(stg), itag(intags))
      
      if ctag(stg) > ctag(intags):
         ctag_grad = s.get_ctag_grad()
         c_init_id = s.getcTagInitID()
      ct = min(ctag(stg), ctag(intags))
       
      o.setSubjTags(alltags(cit, et, inv, it, ct))
      o.set_grad([citag_grad, etag_grad, invtag_grad, itag_grad, ctag_grad])
      o.setInitID([ci_init_id, e_init_id, inv_init_id, i_init_id, c_init_id])

   elif event_type in EXECVE_SET:
      assert isinstance(o,Object) and isinstance(s,Subject)
      a = citag(o.tags())
      if citag(o.tags()) != 1.0: 
         a = 0

      if (o.isMatch("/bin/bash")):
         whitelisted = True

      if (whitelisted == False):
         stg = s.tags()
         cit = citag(stg)
         et = etag(stg)
         citag_grad, etag_grad, itag_grad, ctag_grad = s.get_grad()
         ci_init_id, e_init_id, i_init_id, c_init_id = o.getInitID()
         # citag_grad = s.get_citag_grad()
         # etag_grad = s.get_etag_grad()
         # itag_grad = s.get_itag_grad()
         # ctag_grad = s.get_ctag_grad()
         # citag_grad, etag_grad, invtag_grad, itag_grad, ctag_grad = o.get_grad()
         # ci_init_id, e_init_id, inv_init_id, i_init_id, c_init_id = o.getInitID()

         if isTRUSTED(citag(intags)):
            if (isTRUSTED(cit) and isTRUSTED(et)):
               cit = citag(intags)
               citag_grad = o.get_itag_grad()
               s.setSubjTags([cit, et, 1.0, 1.0])
               s.set_grad([citag_grad, etag_grad, 1.0, 1.0])
               s.setInitID([o.getiTagInitID(), etag_grad, None, None])
            elif (isTRUSTED(cit) and isUNTRUSTED(et)):
               cit = citag(intags)
               citag_grad = o.get_itag_grad()
               ci_init_id = o.getiTagInitID()

               if itag(stg) > itag(intags):
                  itag_grad = o.get_itag_grad()
                  i_init_id = o.getiTagInitID()
               it = min(itag(stg), itag(intags))

               if ctag(stg) > ctag(intags):
                  ctag_grad = o.get_ctag_grad()
                  c_init_id = o.getcTagInitID()
               ct = min(ctag(stg), ctag(intags))

               s.setSubjTags([cit, et, it, ct])
               s.set_grad([citag_grad, etag_grad, itag_grad, ctag_grad])
               s.setInitID([ci_init_id, etag_grad, i_init_id, c_init_id])
            else:
               cit = citag(intags)
               citag_grad = 1.0 * o.get_itag_grad()
               s.setciTagInitID(o.getiTagInitID())

               et = 1 - citag(intags)
               etag_grad = -1.0 * o.get_itag_grad()
               s.seteTagInitID(o.getiTagInitID())

               if itag(stg) > itag(intags):
                  itag_grad = o.get_itag_grad()
                  i_init_id = o.getiTagInitID()
               it = min(itag(stg), itag(intags))

               if ctag(stg) > ctag(intags):
                  ctag_grad = o.get_ctag_grad()
                  c_init_id = o.getcTagInitID()
               ct = min(ctag(stg), ctag(intags))
               
               s.setSubjTags([cit, et, it, ct])
               s.set_grad([citag_grad, etag_grad, itag_grad, ctag_grad])
               s.setInitID([ci_init_id, etag_grad, i_init_id, c_init_id])
         # else:
         #    cit = citag(intags)
         #    citag_grad = o.get_itag_grad()
         #    s.setciTagInitID(o.getiTagInitID())
         #    et = citag(intags)
         #    etag_grad = o.get_itag_grad()
         #    s.seteTagInitID(o.getiTagInitID())
         #    if itag(stg) > itag(intags):
         #       itag_grad = o.get_itag_grad()
         #       s.setiTagInitID(o.getiTagInitID())
         #    it = min(itag(stg), itag(intags))
         #    if ctag(stg) > ctag(intags):
         #       ctag_grad = o.get_ctag_grad()
         #       s.setcTagInitID(o.getcTagInitID())
         #    ct = min(ctag(stg), ctag(intags))
         # inv = UNTRUSTED
         # invtag_grad = 0
         # s.setinvTagInitID(None)
         # s.setSubjTags(alltags(cit, et, inv, it, ct))
         # s.set_grad([citag_grad, etag_grad, invtag_grad, itag_grad, ctag_grad])

   # elif event_type in SET_UID_SET :
   #    assert isinstance(o,Subject)
   #    st = s.tags()
   #    citag_grad, etag_grad, itag_grad, ctag_grad = s.get_grad()
   #    ci_init_id, e_init_id, i_init_id, c_init_id = s.getInitID()
   #    new_owner = morse.Principals[o.owner]
   #    if isRoot(new_owner) == False:
   #       o.setSubjTags([citag(st), etag(st), itag(st), ctag(st)])
   #       o.set_grad([citag_grad, etag_grad, itag_grad, ctag_grad])
   #       o.setInitID([ci_init_id, e_init_id, i_init_id, c_init_id])
      
   elif event_type in CREATE_SET:
      assert isinstance(s, Subject) and isinstance(o, Object)
      st = s.tags()
      sit = itag(st)
      sct = ctag(st)
      itag_grad = s.get_itag_grad()
      ctag_grad = s.get_ctag_grad()
      ci_init_id, e_init_id, i_init_id, c_init_id = s.getInitID()
      
      o.setObjTags([sit, sct])
      o.setiTagInitID(i_init_id)
      o.setcTagInitID(c_init_id)
      o.set_grad([itag_grad, ctag_grad])

   elif event_type in WRITE_SET:
      assert isinstance(s,Subject) and isinstance(o,Object)
      stg = s.tags()
      it = itag(stg)
      ct = ctag(stg)
      citag_grad, etag_grad, itag_grad, ctag_grad = s.get_grad()
      ci_init_id, e_init_id, i_init_id, c_init_id = s.getInitID()

      otg = o.tags()
      itag_grad = o.get_itag_grad()
      ctag_grad = o.get_ctag_grad()
      isiTagChanged = False
      iscTagChanged = False

      if (isTRUSTED(citag(stg)) and isTRUSTED(etag(stg))):
         new_it = it + ab
         new_ct = ct + ab
         new_it = min(1, new_it)
         new_ct = min(1, new_ct)
      elif (isTRUSTED(citag(stg)) and isUNTRUSTED(etag(stg))): 
         new_it = it + ae
         new_ct = ct + ae
         new_it = min(1, new_it)
         new_ct = min(1, new_ct)
      else:
         new_it = it
         new_ct = ct

      if itag(otg) > new_it:
         isiTagChanged = True
      it = min(itag(otg), new_it)
      if ctag(otg) > new_ct:
         iscTagChanged = True
      ct = min(ctag(otg), new_ct)
      newtags = [it, ct]

      if (o.isIP() == False and o.isMatch("UnknownObject")== False):
         o.setObjTags(newtags)
         if isiTagChanged:
            o.set_itag_grad(itag_grad)
            o.setiTagInitID(i_init_id)
         if iscTagChanged:
            o.set_ctag_grad(ctag_grad)
            o.setcTagInitID(c_init_id)
   
   elif event_type in CLONE_SET:
      assert isinstance(o,Subject) and isinstance(s,Subject)
      o.setSubjTags(s.tags())
      o.set_grad(s.get_grad())
      o.setInitID(s.getInitID())

   elif event_type in UPDATE_SET:
      assert isinstance(o,Object) and isinstance(s,Object)
      initag = s.tags()
      o.setObjTags([initag[2],initag[3]])
      o.set_grad([s.get_itag_grad(), s.get_ctag_grad()])
      o.setiTagInitID(s.getiTagInitID())
      o.setcTagInitID(s.getcTagInitID())
      return

   
   if 0 <= event_type < len(standard_events) and s and o:
      assert isinstance(s,Subject)
      diff = 0
      stg = s.tags()
      it = itag(stg)
      ct = ctag(stg)
      et = etag(stg)
      citag_grad, etag_grad, itag_grad, ctag_grad = s.get_grad()
      ts = event['timestamp']
      if (s.updateTime == 0):
         s.updateTime = ts
      elif (isTRUSTED(citag(stg)) and isTRUSTED(etag(stg))):
         diff = (ts - s.updateTime) / 4000000000
         temp = pow(dpi, diff)
         nit = temp * it + (1 - temp) * 0.75
         temp = pow(dpc, diff)
         nct = temp * ct + (1 - temp) * 0.75
         if nit > it:
            itag_grad *= temp
         it = max(it, nit)
         if nct > ct:
            ctag_grad *= temp
         ct = max(ct, nct)
         s.setSubjTags([citag(stg), et, it, ct])
         s.set_grad([citag_grad, etag_grad, itag_grad, ctag_grad])
      
      elif (isTRUSTED(citag(stg)) and isUNTRUSTED(etag(stg))):
         diff = (ts - s.updateTime) / 4000000000
         temp = pow(dpi, diff)
         nit = temp * it + (1 - temp) * 0.45
         temp = pow(dpc, diff)
         nct = temp * ct + (1 - temp) * 0.45
         if (nit < 0.5):
            if nit > it:
               itag_grad *= temp
            it = max(it, nit)
            if nct > ct:
               ctag_grad *= temp
            ct = max(ct, nct)
      
         s.setSubjTags([citag(stg), et, it, ct])
         s.set_grad([citag_grad, etag_grad, itag_grad, ctag_grad])


