#!/usr/bin/env python
# coding: utf-8

#     Author: Saman Firdaus Chishti   |   chishti@gfz-potsdam.de
# 
#     Start date: 29-02-2024
# 
#     
# **Description:** This set of code has been developed to check whether all the values entered in a Heatflow database adhere to a controlled vocabulary and proper structure. It generates an error message for each entry where the value entered is out of bounds and does not meet the assigned criteria. The code also enables checking the vocabulary for multiple values entered in a single column for a particular Heatflow data entry.
# This is in compliance with the paper by Fuchs et al. (2023) titled "[Quality-assurance of heat-flow data: The new structure and evaluation scheme of the IHFC Global Heat Flow Database](https://doi.org/10.1016/j.tecto.2023.229976)," published in Tectonophysics 863: 229976. Also revised for the newer release 2024.
# 
# The code is intended to be published on the GFZ website for the global scientific community to check if any Heatflow dataset adheres to the data structure described in the aforementioned scientific paper. It's a recommended prerequisite before calculating 'Quality Scores' for a given Heatflow dataset. The code for calculating 'Quality Scores' is provided in a separate document.

# ![Vocab Image](Graphics/Vocab.jpg)

# # 1. Importing libraries

# In[1]:

import pandas as pd
import numpy as np
import math
from datetime import datetime
import glob
import os
import warnings
import time
import openpyxl
import re

#get_ipython().run_cell_magic('time', '', 'import pandas as pd\nimport numpy as np\nimport math\nfrom datetime import datetime\nimport openpyxl\nimport warnings\nimport glob\nimport os\nimport re\n')

# In[2]:


warnings.filterwarnings("ignore", category=UserWarning, module='openpyxl')


# # 2. Preparing dataframes

# ## 2.1. Convert to .csv utf-8 format

#     [Description]: Convert all the Heatflow database files within a folder in the usual Excel sheet format to .csv format. Which is easily compatible for the functions mentioned below.

# In[3]:


def convert2UTF8csv(folder_path):    
    excel_files = glob.glob(os.path.join(folder_path, '*.xlsx'))

    for excel_file_path in excel_files:
        if excel_file_path.endswith('_vocab_check.xlsx') or excel_file_path.endswith('_scores_result.xlsx'):
            continue

        try:
            excel_file = pd.ExcelFile(excel_file_path, engine='openpyxl')
            
            data_list_sheet = excel_file.parse('data list')
            
            output_csv_file = os.path.splitext(excel_file_path)[0] + '.csv'
            
            data_list_sheet.to_csv(output_csv_file, index=False, encoding='utf-8')
            
            del data_list_sheet
            del excel_file
            
        except ValueError as e:
            print(f"Error processing {excel_file_path}: {e}")
        except Exception as e:
            print(f"An unexpected error occurred while processing {excel_file_path}: {e}")



# # 3. Controlled vocabulary
# ## 3.1. Assigning columns with similar data types to specific list

# In[5]:


NumC = ['P1','P2','P4','P5','P6','P10','P11','C1','C4','C5','C6','C22','C23','C24','C27','C28','C29','C30','C33','C34','C37','C39','C40','C47']
StrC = ['P7','P9','P12','P13','C3','C11','C12','C13','C14','C15','C17','C18','C19','C21','C25','C26','C31','C32','C35','C36','C41','C42','C43','C44','C45','C46','C48']
DateC = ['C38']


# ## 3.2. Numeric value sets

#     [Description]: Assign permissible value ranges for columns that store numeric values. The Allowed range of values are taken from "Appendix A. Structure and field definitions of the IHFC Global Heat Flow Database" in the aforementioned paper. Also revised for the newer release 2024.

# In[6]:


num_data = {
    #'ID': ['P1','P2','P4','P5','P6','P10','P11','C1','C2','C4','C5','C6','C22','C23','C24','C27','C28','C29','C30','C33','C34','C37','C39','C40','C47'],
    'Min': [-999999.9,0,-90.00000,-180.00000,-12000,-12000,-12000,-999999.9,0,0,0,0,0,-273.15 ,-99999.99,-99999.99,-99999.99,-99999.99,0,0,0,0,0,0],
    'Max': [999999.9,999999.9,90.00000,180.00000,9000,9000,9000,999999.9,19999.9,19999.9,999.9,99.99,99.99,999.99,99999.99,99999.99,99999.99,99999.99,99999,99999,999999,99.99,99.99,9999]
}


# In[7]:


ndf = pd.DataFrame(num_data, index=NumC)


# ### 3.2.1. Pivot the DataFrame: Rows become columns

# In[8]:


tndf = ndf.transpose()
tndf


# ## 3.3. String value sets

#     [Description]: Assign the nature of HF data entry extraction metod: borehole/mine or probe sensing. Also provide controlled vocabulary for columns that store string values. By controlled vocabulary it means the permissible options stored as values for a given column. It is possible to store multiple values in the same column for a particular entry. The allowed controlled vocabulary is taken from "Appendix A. Structure and field definitions of the IHFC Global Heat Flow Database" in the aforementioned paper. Also revised for the newer release 2024.


# In[10]:


B = ["[Drilling]","[Drilling-Clustering]","[Mining]","[Tunneling]","[GTM]","[Indirect (GTM-BSR-CPD-etc.)]"]
P = ["[Probing (onshore-lake-river-etc.)]","[Probing (offshore-ocean)]","[Probing-Clustering]"]
U = ["[Other (specify in comments)]","[unspecified]","nan",""];
sP7 = ["[Onshore (continental)]","[Onshore (lake-river-etc.)]","[Offshore (continental)]","[Offshore (marine)]","[Other (specify in comments)]","[unspecified]"];
sP9 = ["[Yes]","[No]","[Unspecified]"];
sC9 = ["[Yes]","[No]"];
sP12 = ["[Drilling]","[Mining]","[Tunneling]","[GTM]","[Indirect (GTM-BSR-CPD-etc.)]","[Probing (onshore-lake-river-etc.)]","[Probing (offshore-ocean)]","[Drilling-Clustering]","[Probing-Clustering]","[Other (specify in comments)]","[unspecified]"];
sP13 = ["[Hydrocarbon]","[Underground storage]","[Geothermal]","[Groundwater]","[Mapping]","[Research]","[Mining]","[Tunneling]","[Other (specify in comments)]","[unspecified]"];
sC3 = ["[Interval method]","[Bullard method]","[Boot-strapping method]","[Other numerical computations]","[Other (specify in comments)]","[unspecified]"];
sC11 = ["[Considered - p]","[Considered - T]","[Considered - pT]","[not considered]","[unspecified]"];
sC12 = ["[Tilt corrected]","[Drift corrected]","[not corrected]","[Corrected (specify in comments)]","[unspecified]"];
sC13=sC14=sC15=sC16=sC17=sC18=sC19 = ["[Present and corrected]","[Present and not corrected]","[Present not significant]","[not recognized]","[unspecified]"];
sC20 = ["[Expedition/Cruise number]","[R/V Ship]","[D/V Platform]","[D/V Glomar Challenger]","[D/V JOIDES Resolution]","[Other (specify in comments)]","[unspecified]"];

sC21 = ["[Single Steel probe (Bullard)]","[Single Steel probe (Bullard) in-situ TC]","[Violin-Bow probe (Lister)]","[Outrigger probe (Von Herzen) in-situ TC]","[Outrigger probe (Haenel) in-situ TC]","[Outrigger probe (Ewing) with corer]","[Outrigger probe (Ewing) without corer]","[Outrigger probe (Lister) with corer]","[Outrigger probe (autonomous) without corer]","[Outrigger probe (autonomous) with corer]","[Submersible probe]","[Other (specify in comments)]","[unspecified]"];
sC31 = ["[LOGeq]","[LOGpert]","[cLOG]","[DTSeq]","[DTSpert]","[cDTS]","[BHT]","[cBHT]","[HT-FT]","[cHT-FT]","[RTDeq]","[RTDpert]","[cRTD]","[CPD]","[XEN]","[GTM]","[BSR]","[BLK]","[ODTT-PC]","[ODTT-TP]","[SUR]","[GRT]","[EGRT]","[unspecified]","[Other (specify in comments)]"];
sC32 = ["[LOGeq]","[LOGpert]","[cLOG]","[DTSeq]","[DTSpert]","[cDTS]","[BHT]","[cBHT]","[HT-FT]","[cHT-FT]","[RTDeq]","[RTDpert]","[cRTD]","[CPD]","[XEN]","[GTM]","[BSR]","[BLK]","[ODTT-PC]","[ODTT-TP]","[GRT]","[EGRT]","[unspecified]","[Other (specify in comments)]"];
sC35=sC36 = ["[Horner plot]","[Cylinder source method]","[Line source explosion method]","[Inverse numerical modelling]","[Other published correction (specify in comments)]","[unspecified]","[not corrected]","[AAPG correction]","[Harrison correction]"];  
sC41 = ["[In-situ probe]","[Core-log integration]","[Core samples]","[Cutting samples]","[Outcrop samples]","[Well-log interpretation]","[Mineral computation]","[Assumed from literature]","[Other (specify in comments)]","[unspecified]"];
sC42 = ["[Actual heat-flow location]","[Other location]","[Literature-unspecified]","[Unspecified]"];
sC43 = ["[Lab - point source]","[Lab - line source - full space]","[Lab - line source - half space]","[Lab - plane source - full space]","[Lab - plane source - half space]","[Lab - other (specify in comments)]","[Probe - pulse technique]","[Well-log - deterministic approach]","[Well-log - empirical equation]","[Estimation - from chlorine content]","[Estimation - from water content-porosity]","[Estimation - from lithology and literature]","[Estimation - from mineral composition]","[unspecified]"];
sC44 = ["[Saturated measured in-situ]","[Recovered]","[Saturated measured]","[Saturated calculated]","[Dry measured]","[Other (specify in comments)]","[unspecified]"];
sC45 = ["[Unrecorded ambient pT conditions]","[Recorded ambient pT conditions]","[Actual in-situ (pT) conditions]","[Replicated in-situ (p)]","[Replicated in-situ (T)]","[Replicated in-situ (pT)]","[Corrected in-situ (p)]","[Corrected in-situ (T)]","[Corrected in-situ (pT)]","[unspecified]"];
sC46 = ["[T - Birch & Clark (1940)]","[T - Tikhomirov (1968)]","[T - Kutas & Gordienko (1971)]","[T - Anand et al. (1973)]","[T - Haenel & Zoth (1973)]","[T - Blesch et al. (1983)]","[T - Sekiguchi (1984)]","[T - Chapman et al. (1984)]","[T - Zoth & Haenel (1988)]","[T - Somerton (1992)]","[T - Sass et al. (1992)]","[T - Funnell et al. (1996)]","[T - Kukkonen et al. (1999)]","[T - Seipold (2001)]","[T - Vosteen & Schellschmidt (2003)]","[T - Sun et al. (2017)]","[T - Miranda et al. (2018)]","[T - Ratcliffe (1960)]","[p - Bridgman (1924)]","[p - Sibbitt (1975)]","[p - Kukkonen et al. (1999)]","[p - Seipold (2001)]","[p - Durutürk et al. (2002)]","[p - Demirci et al. (2004)]","[p - Görgülü et al. (2008)]","[p - Fuchs & Förster (2014)]","[pT - Ratcliffe (1960)]","[pT - Buntebarth (1991)]","[pT - Chapman & Furlong (1992)]","[pT - Emirov et al. (1997)]","[pT - Abdulagatov et al. (2006)]","[pT - Emirov & Ramazanova (2007)]","[pT - Abdulagatova et al. (2009)]","[pT - Ramazanova & Emirov (2010)]","[pT - Ramazanova & Emirov (2012)]","[pT - Emirov et al. (2017)]","[pT - Hyndman et al. (1974)]","[pT - Langseth (1965)]","[Site-specific experimental relationships]","[Other (specify in comments)]","[unspecified]"];
sC48 = ["[Random or periodic depth sampling]","[Characterize formation conductivities]","[Well log interpretation]","[Computation from probe sensing]","[Other (specify in comments)]","[unspecified]"];
#number = 0
#sC48 = [f"[Random or periodic depth sampling ({number})]","[Random or periodic depth sampling]","[Characterize formation conductivities]","[Well log interpretation]","[Computation from probe sensing]","[Other]","[unspecified]"];
check_list1 = ['[sur]','[clog]', '[cdts]', '[cbht]', '[crtd]', '[cht-ft]'];
check_list2 = ['[clog]', '[cdts]', '[cbht]', '[crtd]', '[cht-ft]'];
check_list3 = [
    "[Unrecorded ambient pT conditions]",
    "[Recorded ambient pT conditions]",
    "[Actual in-situ (pT) conditions]",
    "[Replicated in-situ (p)]",
    "[Replicated in-situ (T)]",
    "[Replicated in-situ (pT)]",
    "[unspecified]"
]

# Convert list items to lowercase once
check_list3 = [v.lower() for v in check_list3]

# In[12]:



sC25 = ["acidic_igneous_material",
"acidic_igneous_rock",
"alkali_feldspar_granite",
"alkali_feldspar_rhyolite",
"alkali_feldspar_syenite",
"alkali_feldspar_syenitic_rock",
"alkali_feldspar_trachyte",
"alkali_feldspar_trachytic_rock",
"alkali-olivine_basalt",
"amphibolite",
"andesite",
"anorthosite",
"anorthositic_rock",
"anthracite_coal",
"anthropogenic_material",
"anthropogenic_unconsolidated_material",
"aphanite",
"aplite",
"arenite",
"ash_and_lapilli",
"ash_breccia_bomb_or_block_tephra",
"ash_tuff_lapillistone_and_lapilli_tuff",
"basalt",
"basanite",
"basanitic_foidite",
"basic_igneous_material",
"basic_igneous_rock",
"bauxite",
"biogenic_sediment",
"biogenic_silica_sedimentary_rock",
"bituminous_coal",
"boninite",
"boulder_gravel_size_sediment",
"boundstone",
"breccia",
"breccia_gouge_series",
"calcareous_carbonate_sediment",
"calcareous_carbonate_sedimentary_material",
"calcareous_carbonate_sedimentary_rock",
"carbonate_mud",
"carbonate_mudstone",
"carbonate_ooze",
"carbonate_rich_mud",
"carbonate_rich_mudstone",
"carbonate_sediment",
"carbonate_sedimentary_material",
"carbonate_sedimentary_rock",
"carbonate_wackestone",
"carbonatite",
"cataclasite_series",
"chalk",
"chemical_sedimentary_material",
"chlorite_actinolite_epidote_metamorphic_rock",
"clastic_sediment",
"clastic_sedimentary_material",
"clastic_sedimentary_rock",
"clay",
"claystone",
"coal",
"cobble_gravel_size_sediment",
"composite_genesis_material",
"composite_genesis_rock",
"compound_material",
"clastic_conglomerate",
"crystalline_carbonate",
"dacite",
"diamictite",
"diamicton",
"diorite",
"dioritic_rock",
"dioritoid",
"doleritic_rock",
"dolostone",
"dolomitic_or_magnesian_sedimentary_material",
"dolomitic_or_magnesian_sedimentary_rock",
"dolomitic_sediment",
"duricrust",
"eclogite",
"evaporite",
"exotic_alkaline_rock",
"exotic_composition_igneous_rock",
"exotic_evaporite",
"fault_related_material",
"fine_grained_igneous_rock",
"foid_bearing_alkali_feldspar_syenite",
"foid_bearing_alkali_feldspar_trachyte",
"foid_bearing_anorthosite",
"foid_bearing_diorite",
"foid_bearing_gabbro",
"foid_bearing_latite",
"foid_bearing_monzodiorite",
"foid_bearing_monzogabbro",
"foid_bearing_monzonite",
"foid_bearing_syenite",
"foid_bearing_trachyte",
"foid_diorite",
"foid_dioritoid",
"foid_gabbro",
"foid_gabbroid",
"foid_monzodiorite",
"foid_monzogabbro",
"foid_monzosyenite",
"foid_syenite",
"foid_syenitoid",
"foidite",
"foiditoid",
"foidolite",
"foliated_metamorphic_rock",
"fragmental_igneous_material",
"fragmental_igneous_rock",
"framestone",
"gabbro",
"gabbroic_rock",
"gabbroid",
"generic_conglomerate",
"generic_mudstone",
"generic_sandstone",
"glass_rich_igneous_rock",
"glassy_igneous_rock",
"glaucophane_lawsonite_epidote_metamorphic_rock",
"gneiss",
"grainstone",
"granite",
"granitoid",
"granodiorite",
"granofels",
"granulite",
"gravel",
"gravel_size_sediment",
"rock_gypsum_or_anhydrite",
"high_magnesium_fine_grained_igneous_rocks",
"hornblendite",
"hornfels",
"hybrid_sediment",
"hybrid_sedimentary_rock",
"igneous_material",
"igneous_rock",
"impact_generated_material",
"impure_calcareous_carbonate_sediment",
"impure_carbonate_sediment",
"impure_carbonate_sedimentary_rock",
"impure_dolostone",
"impure_dolomitic_sediment",
"impure_limestone",
"intermediate_composition_igneous_material",
"intermediate_composition_igneous_rock",
"iron_rich_sediment",
"iron_rich_sedimentary_material",
"iron_rich_sedimentary_rock",
"kalsilitic_and_melilitic_rock",
"komatiitic_rock",
"latite",
"latitic_rock",
"lignite",
"limestone",
"marble",
"material_formed_in_surficial_environment",
"metamorphic_rock",
"metasomatic_rock",
"mica_schist",
"migmatite",
"monzodiorite",
"monzodioritic_rock",
"monzogabbro",
"monzogabbroic_rock",
"monzogranite",
"monzonite",
"monzonitic_rock",
"mud",
"mud_size_sediment",
"clastic_mudstone",
"mylonitic_rock",
"natural_unconsolidated_material",
"non_clastic_siliceous_sediment",
"non_clastic_siliceous_sedimentary_material",
"non_clastic_siliceous_sedimentary_rock",
"ooze",
"organic_bearing_mudstone",
"organic_rich_sediment",
"organic_rich_sedimentary_material",
"organic_rich_sedimentary_rock",
"orthogneiss",
"packstone",
"paragneiss",
"peat",
"pebble_gravel_size_sediment",
"pegmatite",
"peridotite",
"phaneritic_igneous_rock",
"phonolilte",
"phonolitic_basanite",
"phonolitic_foidite",
"phonolitic_tephrite",
"phonolitoid",
"phosphate_rich_sediment",
"phosphate_rich_sedimentary_material",
"phosphorite",
"phyllite",
"phyllonite",
"porphyry",
"pure_calcareous_carbonate_sediment",
"pure_carbonate_mudstone",
"pure_carbonate_sediment",
"pure_carbonate_sedimentary_rock",
"pure_dolomitic_sediment",
"pyroclastic_material",
"pyroclastic_rock",
"pyroxenite",
"quartz_alkali_feldspar_syenite",
"quartz_alkali_feldspar_trachyte",
"quartz_anorthosite",
"quartz_diorite",
"quartz_gabbro",
"quartz_latite",
"quartz_monzodiorite",
"quartz_monzogabbro",
"quartz_monzonite",
"quartz_rich_igneous_rock",
"quartz_syenite",
"quartz_trachyte",
"quartzite",
"residual_material",
"rhyolite",
"rhyolitoid",
"rock",
"rock_salt",
"sand",
"sand_size_sediment",
"clastic_sandstone",
"sapropel",
"schist",
"sediment",
"sedimentary_material",
"sedimentary_rock",
"serpentinite",
"shale",
"silicate_mud",
"silicate_mudstone",
"siliceous_ooze",
"silt",
"siltstone",
"skarn",
"slate",
"spilite",
"syenite",
"syenitic_rock",
"syenitoid",
"syenogranite",
"tephra",
"tephrite",
"tephritic_foidite",
"tephritic_phonolite",
"tephritoid",
"tholeiitic_basalt",
"tonalite",
"trachyte",
"trachytic_rock",
"trachytoid",
"travertine",
"tuff_breccia_agglomerate_or_pyroclastic_breccia",
"tuffite",
"ultrabasic_igneous_rock",
"ultramafic_igneous_rock",
"unconsolidated_material",
"wacke"
]



# In[13]:



sC26 = ["Aalenian",
"Aeronian",
"Albian",
"Anisian",
"Aptian",
"Aquitanian",
"Archean",
"Artinskian",
"Asselian",
"Bajocian",
"Barremian",
"Bartonian",
"Bashkirian",
"Bathonian",
"Berriasian",
"Burdigalian",
"Calabrian",
"Callovian",
"Calymmian",
"Cambrian",
"CambrianSeries2",
"CambrianSeries3",
"CambrianStage10",
"CambrianStage2",
"CambrianStage3",
"CambrianStage4",
"CambrianStage5",
"Campanian",
"Capitanian",
"Carboniferous",
"Carnian",
"Cenomanian",
"Cenozoic",
"Changhsingian",
"Chattian",
"MiddlePleistocene",
"Cisuralian",
"Coniacian",
"Cretaceous",
"Cryogenian",
"Danian",
"Dapingian",
"Darriwilian",
"Devonian",
"Drumian",
"LowerCretaceous",
"LowerDevonian",
"LowerJurassic",
"LowerMississippian",
"LowerOrdovician",
"LowerPennsylvanian",
"LowerTriassic",
"Ectasian",
"Ediacaran",
"Eifelian",
"Emsian",
"Eoarchean",
"Eocene",
"Famennian",
"Floian",
"Fortunian",
"Frasnian",
"Furongian",
"Gelasian",
"Givetian",
"Gorstian",
"Greenlandian",
"Guadalupian",
"Guzhangian",
"Gzhelian",
"Hadean",
"Hauterivian",
"Hettangian",
"Hirnantian",
"Holocene",
"Homerian",
"Induan",
"Ionian",
"Jiangshanian",
"Jurassic",
"Kasimovian",
"Katian",
"Kimmeridgian",
"Kungurian",
"Ladinian",
"Langhian",
"UpperCretaceous",
"UpperDevonian",
"UpperJurassic",
"UpperMississippian",
"UpperOrdovician",
"UpperPennsylvanian",
"UpperPleistocene",
"UpperTriassic",
"Llandovery",
"Lochkovian",
"Lopingian",
"Ludfordian",
"Ludlow",
"Lutetian",
"Maastrichtian",
"Meghalayan",
"Mesoarchean",
"Mesoproterozoic",
"Mesozoic",
"Messinian",
"Miaolingian",
"MiddleDevonian",
"MiddleJurassic",
"MiddleMississippian",
"MiddleOrdovician",
"MiddlePennsylvanian",
"MiddleTriassic",
"Miocene",
"Mississippian",
"Moscovian",
"Neoarchean",
"Neogene",
"Neoproterozoic",
"Norian",
"Northgrippian",
"Olenekian",
"Oligocene",
"Ordovician",
"Orosirian",
"Oxfordian",
"Paibian",
"Paleoarchean",
"Paleocene",
"Paleogene",
"Paleoproterozoic",
"Paleozoic",
"Pennsylvanian",
"Permian",
"Phanerozoic",
"Piacenzian",
"Pleistocene",
"Pliensbachian",
"Pliocene",
"Pragian",
"Precambrian",
"Priabonian",
"Pridoli",
"Proterozoic",
"Quaternary",
"Rhaetian",
"Rhuddanian",
"Rhyacian",
"Roadian",
"Rupelian",
"Sakmarian",
"Sandbian",
"Santonian",
"Selandian",
"Serpukhovian",
"Serravallian",
"Sheinwoodian",
"Siderian",
"Silurian",
"Sinemurian",
"Statherian",
"Stenian",
"Telychian",
"Terreneuvian",
"Thanetian",
"Tithonian",
"Toarcian",
"Tonian",
"Tortonian",
"Tournaisian",
"Tremadocian",
"Triassic",
"Turonian",
"Valanginian",
"Visean",
"Wenlock",
"Wordian",
"Wuchiapingian",
"Wuliuan",
"Ypresian",
"Zanclean"]




#     [Description]: To avoid case-sensitivity issues in the controlled vocabulary

# In[11]:


B = [item.lower() for item in B]
P = [item.lower() for item in P]
U = [item.lower() for item in U]


#     [Description]: To store the controlled vocabulary in a dataframe structure

# In[12]:


str_data = {
    #'ID': ['P7','P9','P12','P13','C3','C11','C12','C13','C14','C15','C17','C18','C19','C21','C31','C32','C35','C36','C41','C42','C43','C44','C45','C46','C48'],#,C20
    'Values': [sP7,sP9,sP12,sP13,sC3,sC11,sC12,sC13,sC14,sC15,sC17,sC18,sC19,sC21,sC25,sC26,sC31,sC32,sC35,sC36,sC41,sC42,sC43,sC44,sC45,sC46,sC48],#,sC20
}


# In[13]:


sdf = pd.DataFrame(str_data, index=StrC)


# ### 3.3.1. Pivot the DataFrame: Rows become columns

# In[14]:


tsdf = sdf.transpose()
tsdf


# ## 3.4. Case sensitivity issue

#     [Description]: To avoid case-sensitivity issues in the controlled vocabulary

# In[15]:


for col in tsdf.columns:
    for id in tsdf.index:
        if isinstance(tsdf.loc[id, col], list):
            tsdf.loc[id, col] = [str(item).lower() for item in tsdf.loc[id, col]]
tsdf


# # 4. Remove extra rows

#     [Description]: To perform computations on the entered HF entries only and skip the column labels. There are two conditions: firstly, when the first cell of the dataframe has the column label 'Obligation', the top 8 rows are considered description. Secondly, when the first cell has the column label 'Short Name', the top 2 rows are considered description. The function 'remove_rows()' below switches between these two conditions and removes the description to prepare the dataframe for operability with other functions.

# In[16]:


def remove_rows(df):
    if df.at[0,'ID'] == 'Obligation':
        df_copy = df
        top_rows = df_copy.index[0:7]
        df_copy = df_copy.drop(df_copy.index[0:7])

        new_index_values = range(1, 1+len(df_copy))
        df_copy.index = new_index_values
        #flag = 6
        return df_copy
    elif df.at[0,'ID'] == 'Short Name':
        df_copy = df
        top_rows = df_copy.index[0:1]
        df_copy = df_copy.drop(df_copy.index[0:1])

        new_index_values = range(1, 1+len(df_copy))
        df_copy.index = new_index_values
        #flag = 1
        return df_copy
    else:
        return df


# # 5. Data type handling

# ## 5.1. Assigning data types to specific columns

#     [Description]: Convert all the columns to string data type. To resolve multiple values in a categorical field for an entry

# In[17]:


def change_type(df):
    df[NumC] = df[NumC].astype(str)
    df[StrC] = df[StrC].astype(str)
    df[DateC] = df[DateC].astype(str)   
    return df


# ## 5.2. Safe float conversion 

# In[18]:


def safe_float_conversion(r):
    r = r.strip()  # Remove any leading or trailing whitespace    
    if r == '0':
        return 0.0    
    try:
        # Check if the first character is a minus sign
        if r[0] == '-':
            return -float(r[1:])  # Convert the substring starting from the second character to float and make it negative
        else:
            return float(r)  # Convert the whole string to float
    except ValueError:
        return None


# # 6. Converting string values to lower case

#     [Description]: To resolve case-sensitivity in the provided Heatflow database

# In[19]:


def toLower(df):
    for col in tsdf.columns:
        for id in df.index:
            df.loc[id, col] = (df.loc[id, col]).lower()
    return df


# # 7. Check relevance

# ## 7.1. Obligation

#     [Description]: Check for mandatory fields indicated by 'Obligation' label in HF database. And store information about the nature of data, whether its borehole or probe sensing.

# In[20]:


def obligation(df):
    m_dict = {}
    domain = {}
    for c in df:
        m_dict[c] = df.loc[0, c]
        domain[c] = df.loc[1, c]
    return m_dict, domain


# ## 7.2.  Structure relevance for the current release

# In[21]:


def relevance(folder_path):
    files = os.listdir(folder_path)
    csv_files = [file for file in files if file.endswith('.csv')]

    if csv_files:
        first_csv_file_path = os.path.join(folder_path, csv_files[0])
        df = pd.read_csv(first_csv_file_path)
        m_dict, domain = obligation(df)
    else:
        print("No CSV files found in the directory. Please run 'convert2UTF8csv(folder_path)' function")
    return m_dict, domain


# # 8. Vocabulary check

#     [Description]: Complete check of vocabulary separately for numeric, string and date type columns

# In[22]:


def vocabcheck(df,m_dict,domain):
    error_df = pd.DataFrame()
    error_msg =pd.DataFrame()
    error_msg_counter = 0

    for id in df.index:
        error_df.loc[id,'A'] = None
        error_df['A'] = error_df['A'].astype("string")

        P12_split = (df.loc[id, 'P12']).split(';')
        
        if any(value in ['[other (specify in comments)]', '[unspecified]'] for value in P12_split):
            error_string = " P12:Quality Check is not possible!,"
        elif any(value == 'nan' for value in P12_split):
            error_string = " P12:Mandatory entry is empty; Quality Check is not possible!,"
        elif any(value in P for value in P12_split) and any(value in B for value in P12_split):
            error_string = " P12:Quality Check is not possible!,"
        else:
            error_string = ""

        error_df.loc[id,'A'] = error_string
        

    for c in NumC:
        min_value = tndf.loc['Min', c]
        max_value = tndf.loc['Max', c]
        
        for id in df.index:
            error_df.loc[id,c] = None
            error_df[c] = error_df[c].astype("string")
            dfvalue = df.loc[id,c]

            P12_split = (df.loc[id, 'P12']).split(';')
            if any(value in U for value in P12_split):
                P12 = ""
            elif any(value in P for value in P12_split) and any(value in B for value in P12_split):
                P12 = ""
            else:
                P12 = P12_split[0] if P12_split else df.loc[id, 'P12']

            while True:
                dfvalue = dfvalue.split(';')
                
                for dfvalue in dfvalue:
                    try:
                        r = dfvalue.strip()
                        if float(r) or r=='0':
                            r = safe_float_conversion(r)
    
                            if  min_value <= r <= max_value:
                                if (c == 'C29') and (df.loc[id, 'C27']) != 'nan':                                    
                                    values_in_c31 = df.loc[id, 'C31'].split(';') if isinstance(df.loc[id, 'C31'], str) else []
                                    values_in_c32 = df.loc[id, 'C32'].split(';') if isinstance(df.loc[id, 'C32'], str) else []
                                    if any(value in check_list1 for value in values_in_c31) or any(value in check_list2 for value in values_in_c32):
                                           error_string = ""
                                    else:
                                           error_string = " C31:or C32 should be corrected!,"
                                else:
                                    error_string = ""
                                
                            elif math.isnan(r):
                                if (m_dict[c] == 'M') and (df.loc[id, c]) == 'nan':
                                    if c == 'C27':
                                        if df.loc[id, 'C29'] == 'nan':
                                            error_string = f" {c}:Mandatory entry is empty!,"
                                        else:
                                            values_in_c31 = df.loc[id, 'C31'].split(';') if isinstance(df.loc[id, 'C31'], str) else []
                                            values_in_c32 = df.loc[id, 'C32'].split(';') if isinstance(df.loc[id, 'C32'], str) else []
                                            if any(value in check_list1 for value in values_in_c31) or any(value in check_list2 for value in values_in_c32):
                                                   error_string = f" {c}:Mandatory entry is empty!,"
                                            else:
                                                   error_string = f" {c}:Mandatory entry is empty!, C31:or C32 should be corrected!,"
                                    elif ('B' in domain[c] and (P12 in B)):
                                        error_string = f" {c}:Mandatory entry is empty!,"
                                    elif ('S' in domain[c] and (P12 in P)):                                        
                                        if (c == 'C4') and (df.loc[id, 'P6']) != 'nan':
                                            error_string = ""
                                        else:
                                            error_string = f" {c}:Mandatory entry is empty!,"
                                            
                                    elif ((('B'or'S') in domain[c]) and (P12 in U)):
                                        error_string = f" {c}:Mandatory entry is empty!,"
                                    else:
                                        error_string = ""
                                elif m_dict[c] == 'M':
                                    if P12 in B:
                                        if (c == 'C5') and (df.loc[id, 'C6'] is None):
                                            error_string = f" {c}:Mandatory entry is empty!,"
                                        else:
                                            error_string = ""
                                    elif P12 in P:
                                        if (c == 'C6') and (df.loc[id, 'C5'] is None):
                                            error_string = f" {c}:Mandatory entry is empty!,"
                                        elif (c == 'C23') and ((df.loc[id, 'C31'] or df.loc[id, 'C32']) is None):
                                            error_string = f" {c}:Mandatory entry is empty!,"
                                        else:
                                            error_string = ""
                                else:
                                    error_string = ""
                            else:
                                error_string = f" {c}:range violated," ###                                                                      
                        else:
                            error_string = f" {c}:range violated,"
                    except ValueError:
                            error_string = f" {c}:invalid format," 
                        
                    error_df.loc[id,c] = error_string
                    if error_string != "":
                        error_msg_counter= error_msg_counter+1

                if ';' not in dfvalue:
                    break
                else:
                    dfvalue = dfvalue[-1]
                         
    for c in StrC:
        string_values = tsdf.loc['Values', c]

        for id in df.index:
            error_df.loc[id,c] = None
            error_df[c] = error_df[c].astype("string")
            dfvalue = df.loc[id,c]

            P12_split = (df.loc[id, 'P12']).split(';')

            if any(value in U for value in P12_split):
                P12 = ""
            elif any(value in P for value in P12_split) and any(value in B for value in P12_split):
                P12 = ""
            else:
                P12 = P12_split[0] if P12_split else df.loc[id, 'P12']

            while True:
                dfvalue = dfvalue.split(';')

                for dfvalue in dfvalue:
                    dfvalue = dfvalue.strip()
                    # new modifications
                    '''
                    if (c == 'C48') and (dfvalue == "[random or periodic depth sampling (number)]"):
                        error_string = ""
                    elif (c == 'C48') and (dfvalue.startswith("[random or periodic depth sampling (")):
                        start_idx = dfvalue.find('(')
                        end_idx = dfvalue.find(')')
                        number_str = dfvalue[start_idx + 1:end_idx]
                        
                        try:
                            number = int(number_str)
                            string_values[0] = f"[random or periodic depth sampling ({number})]"
                                                                                 
                            if dfvalue in string_values:
                                error_string = ""
                            else:
                                error_string = f" {c}:vocabulary warning,"
                            
                        except ValueError: 
                            # new modifications
                            error_string = f" {c}:Enter a number,"
                    '''        
                    if (c == 'C43') and ('[egrt]' in (df.loc[id, 'C31'] or df.loc[id, 'C32'])):
                        if dfvalue == "[probe - pulse technique]":
                            error_string = ''
                        else:
                            error_string = f" {c}:Please check TC method!,"

                    elif (c == 'C45'):
                        if (dfvalue in check_list3):
                            error_string = ''
                        elif (str(df.loc[id, 'C46']) in ["[unspecified]","[site-specific experimental relationships]","[other (specify in comments)]"]):
                            error_string = ''
                        elif ((dfvalue == "[corrected in-situ (p)]") and (str(df.loc[id, 'C46']).startswith('[p -'))):
                            error_string = ''
                        elif ((dfvalue == "[corrected in-situ (t)]") and (str(df.loc[id, 'C46']).startswith('[t -'))):
                            error_string = ''
                        elif (dfvalue == "[corrected in-situ (pt)]"):
                            if '[pt -' in str(df.loc[id, 'C46']):
                                error_string = ''
                            elif ('[p -' in str(df.loc[id, 'C46'])) and ('[t -' in str(df.loc[id, 'C46'])):
                                error_string = ''
                            else:
                                error_string = " C46:Please check TC p-T function!,"
                        elif (dfvalue not in ['nan', '[unspecified]']) and (df.loc[id, 'C46'] == 'nan'):
                            error_string = ""#" C46:TC p-T function is missing!,"
                        elif (dfvalue in ['nan', '[unspecified]']) and (df.loc[id, 'C46'] != 'nan'):
                            error_string = f" {c}:TC p-T conditions is missing!,"
                        else:
                            error_string = " C46:Please check TC p-T function!,"

                    elif dfvalue in string_values:
                        error_string = ""
        
                    elif dfvalue == 'nan':
                        if m_dict[c] == 'M':
                            if (c == 'C31' or 'C32') and (df.loc[id, 'C23'] is None):
                                error_string = f" {c}:Mandatory entry is empty!,"
                            elif c == 'C46':
                                if ('corrected' in str(df.loc[id, 'C45']) or 'unspecified' in str(df.loc[id, 'C45'])):
                                    error_string = f" {c}:Mandatory entry is empty!,"
                                else:
                                    error_string = ""
                            else:
                                if ('B' in domain[c] and (P12 in B)):
                                    error_string = f" {c}:Mandatory entry is empty!,"
                                elif ('S' in domain[c] and (P12 in P)):
                                    error_string = f" {c}:Mandatory entry is empty!,"
                                elif ((('B'or'S') in domain[c]) and (P12 in U)):
                                    error_string = f" {c}:Mandatory entry is empty!,"
                                else:
                                    error_string = "" #pass
                        else:
                            error_string = ""       
                    else:
                        error_string = f" {c}:vocabulary warning,"
        
                    error_df.loc[id,c] = error_string
                    if error_string != "":
                        error_msg_counter= error_msg_counter+1
                        
                if ';' not in dfvalue:
                    break
                else:
                    dfvalue = dfvalue[-1]
    
    # Compare the input date with January 1900
    jan_1900 = datetime(1900, 1, 1)
    for id in df.index:
        error_df.loc[id,'C38'] = None
        error_df['C38'] = error_df['C38'].astype("string")
        dfvalue = (df.loc[id,'C38']).lower()

        P12_split = (df.loc[id, 'P12']).split(';')

        if any(value in U for value in P12_split):
            P12 = ""
        elif any(value in P for value in P12_split) and any(value in B for value in P12_split):
            P12 = ""
        else:
            P12 = P12_split[0] if P12_split else df.loc[id, 'P12']

        while True:
                dfvalue = dfvalue.split(';')
                    
                for dfvalue in dfvalue:
                    dfvalue = dfvalue.strip()
                    
                    if dfvalue == '[unspecified]':
                        error_string = ""
                    elif df.loc[id, 'C38'] == 'nan':
                        if ('B' in domain[c] and (P12 in B)):
                            error_string = " C38:Mandatory entry is empty!,"
                        elif ('S' in domain[c] and (P12 in P)):
                            error_string = " C38:Mandatory entry is empty!,"
                        elif ((('B'or'S') in domain[c]) and (P12 in U)):
                            error_string = f" {c}:Mandatory entry is empty!,"
                        else:
                            error_string = "" #pass
                    else:                        
                        try:
                            if dfvalue[-2:] == "99":
                                year = int(dfvalue[:4])
                                input_date = datetime(year, 1, 1)
                            else:
                                input_date = datetime.strptime(dfvalue, '%Y-%m')
                            
                            if input_date.month == 1 and input_date.year >= jan_1900.year:
                                error_string = ""
                            elif input_date >= jan_1900:
                                error_string = ""
                            else:
                                error_string = " C38:range violated"
                        except ValueError:
                            error_string = f" C38:invalid format,"
                    if error_string != "":
                            error_msg_counter= error_msg_counter+1
            
                    error_df.loc[id,'C38'] = error_string
                error_df = error_df.astype("string")
                    
                if ';' not in dfvalue:
                    break
                else:
                    dfvalue = dfvalue[-1]
        
    result = error_df.apply(lambda x: ''.join(x), axis=1)
    result = result.astype("string")
    
    error_msg['Error'] = result

    return error_msg


# # 9. Final check

# ## 9.1 Sort error

# In[23]:


def reorder_errors(error_str):
    #errors = error_str.split(', ')
    errors = re.split(r',\s*', error_str.strip())
    
    p_errors = [e for e in errors if e.startswith('P')]
    c_errors = [e for e in errors if e.startswith('C')]
    
    p_errors_sorted = sorted(p_errors, key=lambda x: int(x[1:x.index(':')]))
    c_errors_sorted = sorted(c_errors, key=lambda x: int(x[1:x.index(':')]))
    
    sorted_errors = p_errors_sorted + c_errors_sorted
    
    sorted_errors_str = ', '.join(sorted_errors)
    
    cleaned_errors_str = re.sub(r',\s*,\s*', ', ', sorted_errors_str)

    if cleaned_errors_str.endswith(','):
        cleaned_errors_str = cleaned_errors_str[:-1]
    
    return cleaned_errors_str


# ## 9.2 Complete check

#     [Description]: Calling previous functions to prepare data and perform vocabulary checking

# In[24]:


def Complete_check(df):
    m_dict, domain = obligation(df)
    result = vocabcheck(toLower(change_type(remove_rows(df))), m_dict, domain)
    result['Error'] = result['Error'].apply(reorder_errors)
    return result


# # 10 Attach to original data

#     [Description]: Attaching the combined results column to the original database with correct indexing.

# In[25]:


def attachOG(og):
    result = Complete_check(og)
    if og.at[0, 'ID'] == 'Obligation':

        result.index = result.index + 6
    elif og.at[0, 'ID'] == 'Short Name':

        result.index = result.index + 1
    
    og = pd.merge(og, result[['Error']], left_index=True, right_index=True, how='left')
    
    return og


# # 11. Result

# ## 11.1 Results of all files in a folder

#     [Description]: To generate results for all the Heatflow database in a folder stored in .csv format 

# In[26]:


def folder_result(folder_path):

    csv_files = glob.glob(os.path.join(folder_path, '*.csv'))    

    for csv_file_path in csv_files:

        df = pd.read_csv(csv_file_path)
        df_result = attachOG(df)

        if df_result['Error'].eq('').all():
            print("There is no error. Data is ready for Quality Check!")
        else:
            output_excel_file = os.path.splitext(csv_file_path)[0] + '_vocab_check.xlsx'        
            df_result.to_excel(output_excel_file, index=False)
            print(f"Result exported: {output_excel_file}")

    for csv_file_path in csv_files:
        os.remove(csv_file_path)


# # 12. hfqa_tool function

#      [Description]: To check the vocabulary for all the HF dataframe files in a folder.

#      [Desclaimer]: When a new data release occurs and the relevancy (indicated by 'Obligation') of a column in the HF data structure is updated, ensure that you place the data structure files with the updated column relevancy into separate folders before running the code!!

# In[27]:


def check_vocabulary():
    folder_path = input("Please enter the file directory for vocabulary check: ")
    convert2UTF8csv(folder_path)
    folder_result(folder_path)


# In[ ]:
start_time = time.time()

check_vocabulary()

elapsed_time = time.time() - start_time
print(f"Execution time: {elapsed_time} seconds")

