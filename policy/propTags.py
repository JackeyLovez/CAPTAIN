import copy
from graph.Subject import Subject
from graph.Object import Object
from policy.floatTags import TRUSTED, UNTRUSTED, BENIGN, PUBLIC
from policy.floatTags import isTRUSTED, isUNTRUSTED
from policy.floatTags import citag, ctag, itag, etag, isRoot
import pdb

def dump_event_feature(event, s, o, o2):
   if o2:
      features = (s.get_name(), event.type, o.get_name(), o2.get_name())
   elif o:
      features = (s.get_name(), event.type, o.get_name())
   else:
      features = (s.get_name(), event.type)
   return features

def cal_lambda_grads(seo, prop_lambda, old_tag, new_tag, old_tag_grads, new_tag_grads):
   lambda_grads = {}
   for key in old_tag_grads.keys():
      if key != seo:
         lambda_grads[key] = prop_lambda * old_tag_grads[key]
   for key in new_tag_grads.keys():
      if key != seo:
         if key not in lambda_grads:
            lambda_grads[key] = (1 - prop_lambda) * new_tag_grads[key]
         else:
            lambda_grads[key] += (1 - prop_lambda) * new_tag_grads[key]
   lambda_grads[seo] = prop_lambda * old_tag_grads.get(seo, 0) + (1-prop_lambda) * new_tag_grads.get(seo, 0) + old_tag - new_tag
   return lambda_grads

def propTags(event, s, o, o2, att, decay, prop_lambda, tau):
   event_type = event.type
   whitelisted = False
   ab = att
   ae = att/2
   dpPow = decay
   db = 1.0/pow(2, dpPow*2)
   de = 1.0/pow(2, dpPow)
   tau_s_ci = tau[0]
   tau_s_e = tau[1]
   tau_s_i = tau[2]
   tau_s_c = tau[3]
   tau_o_ci = tau[4]
   tau_o_e = tau[5]
   tau_o_i = tau[6]
   tau_o_c = tau[7]

   if event_type in {'read'}:
      # assert isinstance(s,Subject) and isinstance(o,Object)
      stg = s.tags()
      otg = o.tags()
      sit = itag(stg)
      oit = itag(otg)
      sct = ctag(stg)
      oct = ctag(otg)

      # if isinstance(o, Object) and o.isIP():
      #    print(str(dump_event_feature(event, s, o, o2)))
      
      if sit > oit:
         s.i_lambda_gradients = cal_lambda_grads(str(dump_event_feature(event, s, o, o2)), prop_lambda, sit, oit, s.i_lambda_gradients, o.i_lambda_gradients)
         sit  = (1-prop_lambda) * oit + prop_lambda * sit
         for key in s.iTag_gradients.keys():
            s.iTag_gradients[key] *= prop_lambda
         for key in o.iTag_gradients.keys():
            if key not in s.iTag_gradients:
               s.iTag_gradients[key] = (1 - prop_lambda) * o.iTag_gradients[key]
            else:
               s.iTag_gradients[key] += (1 - prop_lambda) * o.iTag_gradients[key]
         s.propagation_chain['i'] = o.propagation_chain['i'][:]
         s.propagation_chain['i'].append(str(dump_event_feature(event, s, o, o2)))

      if sct > oct:
         s.c_lambda_gradients = cal_lambda_grads(str(dump_event_feature(event, s, o, o2)), prop_lambda, sct, oct, s.c_lambda_gradients, o.c_lambda_gradients)
         sct = (1-prop_lambda) * oct + prop_lambda * sct
         for key in s.cTag_gradients.keys():
            s.cTag_gradients[key] *= prop_lambda
         for key in o.cTag_gradients.keys():
            if key not in s.cTag_gradients:
               s.cTag_gradients[key] = (1 - prop_lambda) * o.cTag_gradients[key]
            else:
               s.cTag_gradients[key] += (1 - prop_lambda) * o.cTag_gradients[key]
         s.propagation_chain['c'] = o.propagation_chain['c'][:]
         s.propagation_chain['c'].append(str(dump_event_feature(event, s, o, o2)))

      s.setSubjTags([citag(stg), etag(stg), sit, sct])
      s.updateTime = event.time

   elif event_type in {'create'}:
      assert isinstance(s, Subject) and isinstance(o, Object)
      st = s.tags()
      sit = itag(st)
      sct = ctag(st)

      o.setObjTags([sit, sct])
      o.iTag_gradients = copy.deepcopy(s.iTag_gradients)
      o.cTag_gradients = copy.deepcopy(s.cTag_gradients)
      o.propagation_chain['i'] = s.propagation_chain['i'][:]
      o.propagation_chain['i'].append(str(dump_event_feature(event, s, o, o2)))
      o.propagation_chain['c'] = s.propagation_chain['c'][:]
      o.propagation_chain['c'].append(str(dump_event_feature(event, s, o, o2)))
      o.i_lambda_gradients = copy.deepcopy(s.i_lambda_gradients)
      o.c_lambda_gradients = copy.deepcopy(s.c_lambda_gradients)
      o.updateTime = event.time

   elif event_type in {'write'}:
      assert isinstance(s,Subject) and isinstance(o,Object)
      if (o.isIP() == False and o.isMatch("UnknownObject")== False):
         stg = s.tags()
         otg = o.tags()
         it = itag(stg)
         ct = ctag(stg)

         if (isTRUSTED(citag(stg), tau_s_ci) and isTRUSTED(etag(stg), tau_s_e)):
            new_it = min(1, it + ab)
            new_ct = min(1, ct + ab)
         elif (isTRUSTED(citag(stg), tau_s_ci) and isUNTRUSTED(etag(stg), tau_s_e)): 
            new_it = min(1, it + ae)
            new_ct = min(1, ct + ae)
         else:
            new_it = it
            new_ct = ct

         if itag(otg) > new_it:
            o.setObjiTag((1-prop_lambda) * new_it + prop_lambda * itag(otg))
            for key in o.iTag_gradients.keys():
               o.iTag_gradients[key] *= prop_lambda
            for key in s.iTag_gradients.keys():
               if key not in o.iTag_gradients:
                  o.iTag_gradients[key] = (1 - prop_lambda) * s.iTag_gradients[key]
               else:
                  o.iTag_gradients[key] += (1 - prop_lambda) * s.iTag_gradients[key]
            o.propagation_chain['i'] = s.propagation_chain['i'][:]
            o.propagation_chain['i'].append(str(dump_event_feature(event, s, o, o2)))
            o.i_lambda_gradients = cal_lambda_grads(str(dump_event_feature(event, s, o, o2)), prop_lambda, itag(otg), new_it, o.i_lambda_gradients, s.i_lambda_gradients)

         if ctag(otg) > new_ct:
            o.setObjcTag((1-prop_lambda) * new_ct + prop_lambda * ctag(otg))
            for key in o.cTag_gradients.keys():
               o.cTag_gradients[key] *= prop_lambda
            for key in s.cTag_gradients.keys():
               if key not in o.cTag_gradients:
                  o.cTag_gradients[key] = (1 - prop_lambda) * s.cTag_gradients[key]
               else:
                  o.cTag_gradients[key] += (1 - prop_lambda) * s.cTag_gradients[key]
            o.propagation_chain['c'] = s.propagation_chain['c'][:]
            o.propagation_chain['c'].append(str(dump_event_feature(event, s, o, o2)))
            o.c_lambda_gradients = cal_lambda_grads(str(dump_event_feature(event, s, o, o2)), prop_lambda, ctag(otg), new_ct, o.c_lambda_gradients, s.c_lambda_gradients)
         
         o.updateTime = event.time
            

   elif event_type in {'load'}:
      assert isinstance(s, Subject) and isinstance(o, Object) and o.isFile()
      if o.isFile():
         stg = s.tags()
         otg = o.tags()
         cit = citag(stg)
         it = itag(stg)
         ct = ctag(stg)

         if citag(stg) > citag(o.tags()):
            cit = (1-prop_lambda) * citag(otg) + prop_lambda * citag(stg)
            for key in s.ciTag_gradients.keys():
               s.ciTag_gradients[key] *= prop_lambda
            for key in o.iTag_gradients.keys():
               if key not in s.ciTag_gradients:
                  s.ciTag_gradients[key] = (1 - prop_lambda) * o.iTag_gradients[key]
               else:
                  s.ciTag_gradients[key] += (1 - prop_lambda) * o.iTag_gradients[key]
            s.ci_lambda_gradients = cal_lambda_grads(str(dump_event_feature(event, s, o, o2)), prop_lambda, citag(stg), citag(o.tags()), s.ci_lambda_gradients, o.i_lambda_gradients)

         if itag(stg) > itag(otg):
            it = (1-prop_lambda) * itag(otg) + prop_lambda * itag(stg)
            for key in s.iTag_gradients.keys():
               s.iTag_gradients[key] *= prop_lambda
            for key in o.iTag_gradients.keys():
               if key not in s.iTag_gradients:
                  s.iTag_gradients[key] = (1 - prop_lambda) * o.iTag_gradients[key]
               else:
                  s.iTag_gradients[key] += (1 - prop_lambda) * o.iTag_gradients[key]
            s.propagation_chain['i'] = o.propagation_chain['i'][:]
            s.propagation_chain['i'].append(str(dump_event_feature(event, s, o, o2)))
            s.i_lambda_gradients = cal_lambda_grads(str(dump_event_feature(event, s, o, o2)), prop_lambda, itag(stg), itag(otg), s.i_lambda_gradients, o.i_lambda_gradients)

         if ctag(stg) > ctag(otg):
            ct = (1-prop_lambda) * ctag(otg) + prop_lambda * ctag(stg)
            for key in s.cTag_gradients.keys():
               s.cTag_gradients[key] *= prop_lambda
            for key in o.cTag_gradients.keys():
               if key not in s.cTag_gradients:
                  s.cTag_gradients[key] = (1 - prop_lambda) * o.cTag_gradients[key]
               else:
                  s.cTag_gradients[key] += (1 - prop_lambda) * o.cTag_gradients[key]
            s.propagation_chain['c'] = o.propagation_chain['c'][:]
            s.propagation_chain['c'].append(str(dump_event_feature(event, s, o, o2)))
            s.c_lambda_gradients = cal_lambda_grads(str(dump_event_feature(event, s, o, o2)), prop_lambda, ctag(stg), ctag(otg), s.c_lambda_gradients, o.c_lambda_gradients)

         s.setSubjTags([cit, etag(stg), it, ct])
         s.updateTime = event.time

   elif event_type in {'execve'}:
      assert isinstance(o,Object) and isinstance(s,Subject)
      otg = o.tags()

      if (whitelisted == False):
         stg = s.tags()
         cit = citag(stg)
         et = etag(stg)
         it = itag(stg)
         ct = ctag(stg)

         if (isTRUSTED(cit, tau_s_ci) and isTRUSTED(et, tau_s_e)):
            s.setSubjTags([citag(otg), et, 1.0, 1.0])
            s.ciTag_gradients = copy.deepcopy(o.iTag_gradients)
            s.ci_lambda_gradients = copy.deepcopy(o.i_lambda_gradients)
            s.iTag_gradients = {(s.id,'i'): 1.0}
            s.cTag_gradients = {(s.id,'c'): 1.0}
            s.i_lambda_gradients = {}
            s.c_lambda_gradients = {}
            s.propagation_chain['i'] = []
            s.propagation_chain['c'] = []
         elif (isTRUSTED(cit, tau_s_ci) and isUNTRUSTED(et, tau_s_e)):
            if it > itag(otg):
               it = (1-prop_lambda) * itag(otg) + prop_lambda * it
               for key in s.iTag_gradients.keys():
                  s.iTag_gradients[key] *= prop_lambda
               for key in o.iTag_gradients.keys():
                  if key not in s.iTag_gradients:
                     s.iTag_gradients[key] = (1 - prop_lambda) * o.iTag_gradients[key]
                  else:
                     s.iTag_gradients[key] += (1 - prop_lambda) * o.iTag_gradients[key]
               s.propagation_chain['i'] = o.propagation_chain['i'][:]
               s.propagation_chain['i'].append(str(dump_event_feature(event, s, o, o2)))
               s.i_lambda_gradients = cal_lambda_grads(str(dump_event_feature(event, s, o, o2)), prop_lambda, itag(stg), itag(otg), s.i_lambda_gradients, o.i_lambda_gradients)

            if ct > ctag(otg):
               ct = (1-prop_lambda) * ctag(otg) + prop_lambda * ct
               for key in s.cTag_gradients.keys():
                  s.cTag_gradients[key] *= prop_lambda
               for key in o.cTag_gradients.keys():
                  if key not in s.cTag_gradients:
                     s.cTag_gradients[key] = (1 - prop_lambda) * o.cTag_gradients[key]
                  else:
                     s.cTag_gradients[key] += (1 - prop_lambda) * o.cTag_gradients[key]
               s.propagation_chain['c'] = o.propagation_chain['c'][:]
               s.propagation_chain['c'].append(str(dump_event_feature(event, s, o, o2)))
               s.c_lambda_gradients = cal_lambda_grads(str(dump_event_feature(event, s, o, o2)), prop_lambda, ctag(stg), ctag(otg), s.c_lambda_gradients, o.c_lambda_gradients)
            
            s.ciTag_gradients = copy.deepcopy(o.iTag_gradients)
            s.ci_lambda_gradients = copy.deepcopy(o.i_lambda_gradients)
            s.setSubjTags([citag(otg), et, it, ct])
         else:
            et = cit
            s.eTag_gradients = copy.deepcopy(s.ciTag_gradients)
            s.e_lambda_gradients = copy.deepcopy(s.ci_lambda_gradients)
            
            cit = citag(otg)
            s.ciTag_gradients = copy.deepcopy(o.iTag_gradients)
            s.ci_lambda_gradients = copy.deepcopy(s.i_lambda_gradients)

            if itag(stg) > itag(otg):
               it = (1-prop_lambda) * itag(otg) + prop_lambda * it
               for key in s.iTag_gradients.keys():
                  s.iTag_gradients[key] *= prop_lambda
               for key in o.iTag_gradients.keys():
                  if key not in s.iTag_gradients:
                     s.iTag_gradients[key] = (1 - prop_lambda) * o.iTag_gradients[key]
                  else:
                     s.iTag_gradients[key] += (1 - prop_lambda) * o.iTag_gradients[key]
               s.propagation_chain['i'] = o.propagation_chain['i'][:]
               s.propagation_chain['i'].append(str(dump_event_feature(event, s, o, o2)))
               s.i_lambda_gradients = cal_lambda_grads(str(dump_event_feature(event, s, o, o2)), prop_lambda, itag(stg), itag(otg), s.i_lambda_gradients, o.i_lambda_gradients)

            if ctag(stg) > ctag(otg):
               ct = (1-prop_lambda) * ctag(otg) + prop_lambda * ct
               for key in s.cTag_gradients.keys():
                  s.cTag_gradients[key] *= prop_lambda
               for key in o.cTag_gradients.keys():
                  if key not in s.cTag_gradients:
                     s.cTag_gradients[key] = (1 - prop_lambda) * o.cTag_gradients[key]
                  else:
                     s.cTag_gradients[key] += (1 - prop_lambda) * o.cTag_gradients[key]
               s.propagation_chain['c'] = o.propagation_chain['c'][:]
               s.propagation_chain['c'].append(str(dump_event_feature(event, s, o, o2)))
               s.c_lambda_gradients = cal_lambda_grads(str(dump_event_feature(event, s, o, o2)), prop_lambda, ctag(stg), ctag(otg), s.c_lambda_gradients, o.c_lambda_gradients)
            
            s.setSubjTags([cit, et, it, ct])
         s.updateTime = event.time   
   
   elif event_type in {'clone'}:
      assert isinstance(o,Subject) and isinstance(s,Subject)
      o.setSubjTags(s.tags())
      o.ciTag_gradients = copy.deepcopy(s.ciTag_gradients)
      o.eTag_gradients = copy.deepcopy(s.eTag_gradients)
      o.iTag_gradients = copy.deepcopy(s.iTag_gradients)
      o.cTag_gradients = copy.deepcopy(s.cTag_gradients)
      o.propagation_chain['i'] = s.propagation_chain['i'][:]
      o.propagation_chain['i'].append(str(dump_event_feature(event, s, o, o2)))
      o.propagation_chain['c'] = s.propagation_chain['c'][:]
      o.propagation_chain['c'].append(str(dump_event_feature(event, s, o, o2)))
      o.ci_lambda_gradients = copy.deepcopy(s.ci_lambda_gradients)
      o.e_lambda_gradients = copy.deepcopy(s.e_lambda_gradients)
      o.i_lambda_gradients = copy.deepcopy(s.i_lambda_gradients)
      o.c_lambda_gradients = copy.deepcopy(s.c_lambda_gradients)
      o.updateTime = event.time

   elif event_type in {'update', 'rename'}:
      assert isinstance(o,Object) and isinstance(o2,Object)
      initag = o.tags()
      o2.setObjTags([initag[2],initag[3]])
      o2.iTag_gradients = copy.deepcopy(o.iTag_gradients)
      o2.cTag_gradients = copy.deepcopy(o.cTag_gradients)
      o2.propagation_chain['i'] = o.propagation_chain['i'][:]
      o2.propagation_chain['i'].append(str(dump_event_feature(event, s, o, o2)))
      o2.propagation_chain['c'] = o.propagation_chain['c'][:]
      o2.propagation_chain['c'].append(str(dump_event_feature(event, s, o, o2)))
      o2.i_lambda_gradients = copy.deepcopy(o.i_lambda_gradients)
      o2.c_lambda_gradients = copy.deepcopy(o.c_lambda_gradients)
      o2.updateTime = event.time

   # elif event_type in {'set_uid'}:
   #    assert isinstance(o,Subject) and isinstance(s,Subject)
   #    o.setSubjTags(s.tags())
   #    o.set_grad(s.get_grad())
   #    o.setInitID(s.getInitID())
   #    o.propagation_chain['i'] = s.propagation_chain['i'][:]
   #    o.propagation_chain['i'].append(str(dump_event_feature(event, s, o, o2)))
   #    o.propagation_chain['c'] = s.propagation_chain['c'][:]
   #    o.propagation_chain['c'].append(str(dump_event_feature(event, s, o, o2)))
   #    o.updateTime = event.time

   if event_type in {'chmod', 'set_uid', 'mprotect', 'mmap', 'remove', 'clone', 'read', 'load', 'execve', 'inject', 'create', 'write'} and s and o:
      assert isinstance(s,Subject)
      diff = 0
      stg = s.tags()
      cit = citag(stg)
      it = itag(stg)
      ct = ctag(stg)
      et = etag(stg)
      ts = event.time
      if (s.updateTime == 0):
         s.updateTime = ts
      elif (isTRUSTED(cit, tau_s_ci) and isTRUSTED(et, tau_s_e)):
         diff = (ts - s.updateTime) / 4e9
         temp = pow(db, diff)
         nit = temp * it + (1 - temp) * 0.75
         nct = temp * ct + (1 - temp) * 0.75
         if it < nit:
            it = nit
            for key in s.iTag_gradients.keys():
               s.iTag_gradients[key] *= temp
            for key in s.i_lambda_gradients.keys():
               s.i_lambda_gradients[key] *= temp
         if ct < ct:
            ct = nct
            for key in s.cTag_gradients.keys():
               s.cTag_gradients[key] *= temp
            for key in s.c_lambda_gradients.keys():
               s.c_lambda_gradients[key] *= temp
         s.setSubjTags([cit, et, it, ct])
         s.updateTime = ts
      
      elif (isTRUSTED(cit, tau_s_ci) and isUNTRUSTED(et, tau_s_e)):
         diff = (ts - s.updateTime) / 4e9
         temp = pow(de, diff)
         nit = temp * it + (1 - temp) * 0.45
         nct = temp * ct + (1 - temp) * 0.45
         # if (nit < tau_s_i):
         if it < nit:
            it = nit
            for key in s.iTag_gradients.keys():
               s.iTag_gradients[key] *= temp
            for key in s.i_lambda_gradients.keys():
               s.i_lambda_gradients[key] *= temp
         if ct < nct:
            ct = nct
            for key in s.cTag_gradients.keys():
               s.cTag_gradients[key] *= temp
            for key in s.c_lambda_gradients.keys():
               s.c_lambda_gradients[key] *= temp
      
         s.setSubjTags([citag(stg), et, it, ct])
         s.updateTime = ts

   if s:
      s.check_gradients()
   if o:
      o.check_gradients()
   if o2:
      o2.check_gradients()