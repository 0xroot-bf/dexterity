#!/usr/bin/python

import sys

from dx.dex import DexParser
from dx.dex import ByteStream
from dx.dex import dxlib

from dx.printer import DexPrinter

def main():    
    target = sys.argv[-1]
    print 'Parsing Dex: %s' % target

    dxp = DexParser(target)

    #header
    header = dxp.item('header')

    #data from header
    link_data = dxp.raw(header.link_off,header.link_size)
    map_list = dxp.item('maplist',header.map_off)
    string_ids = dxp.list('stringid' ,header.string_ids_size ,header.string_ids_off)
    type_ids   = dxp.list('typeid'   ,header.type_ids_size   ,header.type_ids_off)
    proto_ids  = dxp.list('protoid'  ,header.proto_ids_size  ,header.proto_ids_off)
    field_ids  = dxp.list('fieldid'  ,header.field_ids_size  ,header.field_ids_off)
    method_ids = dxp.list('methodid' ,header.method_ids_size ,header.method_ids_off)
    class_defs = dxp.list('classdef' ,header.class_defs_size ,header.class_defs_off)
      
    #data from string id
    string_data_list = dxp.table('stringdata',string_ids,'string_data_off')

    #data from proto id
    type_lists = dxp.table('typelist',proto_ids,'parameters_off')

    #data from class def
    type_lists += dxp.table('typelist',class_defs,'interfaces_off')
    class_annotations = dxp.table('annotationdirectoryitem',class_defs,'annotations_off')
    class_data_list = dxp.table('classdata',class_defs,'class_data_off')
    class_statics = dxp.table('encodedarray',class_defs,'static_values_off')

    #data from class data    
    code_list = []  

    for class_data in class_data_list:
        if class_data.meta.corrupted == True: continue

        for i in xrange(class_data.direct_methods_size.uleb()):
            method = class_data.direct_methods[i].contents
            if method.code_off.uleb() != 0:
                code_list.append(dxp.item('codeitem',method.code_off.uleb()))
        
        for i in xrange(class_data.virtual_methods_size.uleb()):
            method = class_data.virtual_methods[i].contents
            if method.code_off.uleb() != 0:
                code_list.append(dxp.item('codeitem',method.code_off.uleb()))

    #data from code item
    debug_info_list = dxp.table('debuginfo',code_list,'debug_info_off')

    #data from class annotations    
    annotation_sets = dxp.table('annotationsetitem',class_annotations,
                               'class_annotations_off')

    annotation_set_ref_lists = []

    for item in class_annotations:
        if item.meta.corrupted == True: continue

        for i in xrange(item.fields_size):            
            off = item.field_annotations[i].contents.annotations_off
            annotation_sets.append(dxp.item('annotationsetitem',off))

        for i in xrange(item.annotated_methods_size):            
            off = item.method_annotations[i].contents.annotations_off
            annotation_sets.append(dxp.item('annotationsetitem',off))

        for i in xrange(item.annotated_parameters_size):            
            off = item.parameter_annotations[i].contents.annotations_off
            annotation_set_ref_lists.append(dxp.item('annotationsetreflist',off))
            
    #data from annotation set ref lists
    for item in annotation_set_ref_lists:
        if item.meta.corrupted == True: continue

        for i in xrange(item.size):            
            off = item.list[i].contents.annotations_off
            annotation_sets.append(dxp.item('annotationsetitem',off)) 

    #data from annotation set item
    annotations = []
            
    for item in annotation_sets:
        if item.meta.corrupted == True: continue

        for i in xrange(item.size):
            off = item.entries[i].contents.annotation_off
            annotations.append(dxp.item('annotationitem',off))

    opts = ''.join(sys.argv[1:-1]).split('-')
    args = {}

    printer = DexPrinter('debug' in opts)

    for i,opt in enumerate(opts):
        if opt in ['','debug']: continue

        if opt in ['H','X','corrupted','rebuild']:
            args[opt] = True

        elif opt.split(' ')[0] in ['S','T','P','F','M','C','t','s',
                                   'c','B','D','i','a','f','r','n']:
            if len(opt.split()) == 1:
                args[opt] = -1
            elif opt.split(' ')[1].isdigit():
                args[opt.split(' ')[0]] = int(opt.split(' ')[1])
            else:
                print "Invalid Argument for %s : %s" % opt.split(' ')
                sys.exit(-1)
        else:
            print 'Unknown Option: -%s' % opt.split(' ')[0]
            sys.exit(-1)


    if 'H' in args.keys():
        printer.header(header)

    elif 'X' in args.keys():
        printer.maplist(map_list)    

    elif 'corrupted' in args.keys():
        corrupted  = header.meta.corrupted
        corrupted |= map_list.meta.corrupted

        for item in string_ids: corrupted |= item.meta.corrupted
        for item in type_ids: corrupted |= item.meta.corrupted
        for item in proto_ids: corrupted |= item.meta.corrupted
        for item in field_ids: corrupted |= item.meta.corrupted
        for item in method_ids: corrupted |= item.meta.corrupted
        for item in class_defs: corrupted |= item.meta.corrupted

        for item in string_data_list: corrupted |= item.meta.corrupted
        for item in type_lists: corrupted |= item.meta.corrupted
        for item in class_annotations: corrupted |= item.meta.corrupted
        for item in class_data_list: corrupted |= item.meta.corrupted
        for item in class_statics: corrupted |= item.meta.corrupted
        for item in code_list: corrupted |= item.meta.corrupted
        for item in debug_info_list: corrupted |= item.meta.corrupted

        for item in annotation_sets: corrupted |= item.meta.corrupted
        for item in annotation_set_ref_lists: corrupted |= item.meta.corrupted

        for item in annotations: corrupted |= item.meta.corrupted

        print "Corrupted: " + str(corrupted)

    elif 'rebuild' in args.keys():
        bs = ByteStream(size=dxp.bs._bs.contents.size)

        dxlib.dxb_header(bs._bs,header)
        dxlib.dxb_maplist(bs._bs,map_list)

        for item in string_ids: dxlib.dxb_stringid(bs._bs,item)
        for item in type_ids: dxlib.dxb_typeid(bs._bs,item)
        for item in proto_ids: dxlib.dxb_protoid(bs._bs,item)
        for item in field_ids: dxlib.dxb_fieldid(bs._bs,item)
        for item in method_ids: dxlib.dxb_methodid(bs._bs,item)
        for item in class_defs: dxlib.dxb_classdef(bs._bs,item)

        for item in string_data_list: dxlib.dxb_stringdata(bs._bs,item)
        for item in type_lists: dxlib.dxb_typelist(bs._bs,item)
        for item in class_annotations: dxlib.dxb_annotationdirectoryitem(bs._bs,item)
        for item in class_data_list: dxlib.dxb_classdata(bs._bs,item)
        for item in class_statics: dxlib.dxb_encodedarray(bs._bs,item)
        for item in code_list: dxlib.dxb_codeitem(bs._bs,item)
        for item in debug_info_list: dxlib.dxb_debuginfo(bs._bs,item)

        for item in annotation_sets: dxlib.dxb_annotationsetitem(bs._bs,item)
        for item in annotation_set_ref_lists: dxlib.dxb_annotationsetreflist(bs._bs,item)
        for item in annotations: dxlib.dxb_annotationitem(bs._bs,item)
        bs.save("rebuild.dex")

    elif 'S' in args.keys():
        if args.get('S') < 0:
            for item in string_ids:
                printer.stringid(item)
        else:
            printer.stringid(string_ids[args.get('S')])

    elif 'T' in args.keys():
        if args.get('T') < 0:
            for item in type_ids:
                printer.typeid(item)
        else:
            printer.typeid(type_ids[args.get('T')])

    elif 'P' in args.keys():
        if args.get('P') < 0:
            for item in proto_ids:
                printer.protoid(item)
        else:
            printer.protoid(proto_ids[args.get('P')])

    elif 'F' in args.keys():
        if args.get('F') < 0:
            for item in field_ids:
                printer.fieldid(item)
        else:
            printer.fieldid(field_ids[args.get('F')])

    elif 'M' in args.keys():
        if args.get('M') < 0:
            for item in method_ids:
                printer.methodid(item)
        else:
            printer.methodid(method_ids[args.get('M')])

    elif 'C' in args.keys():
        if args.get('C') < 0:
            for item in class_defs:
                printer.classdef(item)
        else:
            printer.classdef(class_defs[args.get('C')])

    elif 't' in args.keys():
        if args.get('t') < 0:
            for item in type_lists:
                printer.typelist(item)
        else:
            printer.typelist(type_lists[args.get('t')])

    elif 's' in args.keys():
        if args.get('s') < 0:
            for item in string_data_list:
                printer.stringdata(item)
        else:
            printer.stringdata(string_data_list[args.get('s')])

    elif 'c' in args.keys():
        if args.get('c') < 0:
            for item in class_data_list:
                printer.classdata(item)
        else:
            printer.classdata(class_data_list[args.get('c')])

    elif 'B' in args.keys():
        if args.get('B') < 0:
            for item in code_list:
                printer.codeitem(item)
        else:
            printer.codeitem(code_list[args.get('B')])

    elif 'D' in args.keys():
        if args.get('D') < 0:
            for item in debug_info_list:
                printer.debuginfo(item)
        else:
            printer.debuginfo(debug_info_list[args.get('B')])

    elif 'i' in args.keys():
        if args.get('i') < 0:
            for item in class_statics:
                printer.encodedarray(item)
        else:
            printer.encodedarray(class_statics[args.get('i')])

    elif 'a' in args.keys():
        if args.get('a') < 0:
            for item in class_annotations:
                printer.annotationdirectoryitem(item)
        else:
            printer.annotationdirectoryitem(class_annotations[args.get('i')])

    elif 'f' in args.keys():
        if args.get('f') < 0:
            for item in annotation_set_ref_lists:
                printer.annotationsetreflist(item)
        else:
            printer.annotationsetreflist(annotation_set_ref_lists[args.get('i')])

    elif 'r' in args.keys():
        if args.get('r') < 0:
            for item in annotation_sets:
                printer.annotationsetitem(item)
        else:
            printer.annotationsetitem(annotation_sets[args.get('i')])


    elif 'n' in args.keys():
        if args.get('n') < 0:
            for item in annotations:
                printer.annotationitem(item)
        else:
            printer.annotationitem(annotations[args.get('i')])

    else:
        print 'Unknown Options.'

if __name__ == '__main__':
    main()
