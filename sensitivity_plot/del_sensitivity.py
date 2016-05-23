#!/usr/bin/env python

"""
 Script to compare the performance (sensitivity) of a structural variant calling tool, specifically for deletions
"""
import sys,os,re
import argparse,subprocess

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

import numpy as np
from tempfile import NamedTemporaryFile 

def vcf_to_bed(fin):
	"""
	reducing vcf to bed coordinates;
	returns a dict of bed coordinates, categorized by bin   
	"""	

	bed_dict = {} 
	svtype = "DEL"
	for bins in range(0,num_bins): bed_dict[bins] = [] #initializing 

	chromosomes = list ((str(a) for a in [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22]))
	masterlist = {}
	
	for lines in open(fin):
	
		if lines.startswith("##"): #info header
			if lines.startswith("##program="):
				prog_name = lines.strip().split('=')[1]
			if lines.startswith("##source="):
				source = lines.strip().split('/')[-1]
			continue
		elif lines.startswith("#"): #useful headers
			header_names = lines.strip("#").split('\t')
			for i in header_names: masterlist[i] = {}
		else:	
			CHROM,POS,ID,REF,ALT,QUAL,FILTER,INFO,FORMAT,SAMPLE = lines.strip().split('\t')	
			inside_info = {}
			
			#print INFO
			expLen = re.compile("^SVLEN") #regular expression for svlen field 
			expEnd = re.compile("^END=") #regex

			for i in INFO.strip().split(";"): 
				if re.match(expLen,i): SIZE  = int(i.strip().split("=")[1])
				if re.match(expEnd,i) : END = int(i.strip().split("=")[1]) 	
			START = int(POS) 
			SVTYPE = ALT.strip(">").strip("<") #check
	
			if SVTYPE == svtype and CHROM in chromosomes:
				if SIZE >= size_min and SIZE <= size_max:
					if SIZE%size_bin == 0 : bin_id = SIZE/size_bin -1  #size slices
					else: bin_id = SIZE/size_bin	
					bedentry = (CHROM,START,END) #tuple	
					bed_dict[bin_id].append(bedentry)
				else: continue 	
					
	return bed_dict 

def plot_sensitivity(plot_container,tru_title,figno):
	"""
	Plotting sensitivity. Number of plots depends on number of truth sets provided.
	One plot per truth set.
	"""
	plt.figure(figno)	

	colours = list('byrk') + ['MediumSpringGreen','Sienna','Purple','Khaki','SlateGray','Green'] 
	plt.gca().set_color_cycle(colours)
	
	for id in sorted(plot_container):

		delx,dely = plot_container[id][0],plot_container[id][1]		
		plt.plot(delx[::-1],dely[::-1],linestyle='--',marker = 'o',label=id)

	plt.xlabel('size of deletion')
	plt.ylabel('portion of truth calls recovered (sensitivity)')
	title = ("Sensitivity plot at %d %% reciprocal overlap\nTruth set: %s" %(pct_ovl*100,tru_title)) 
	plt.title(title)
	plt.axis([0,size_max,0.0,1.0])
	plt.grid(True)
	plt.legend(loc='best',fontsize='x-small')  	
	
	fig_name="Sensitivity_summary_"+tru_title+".png" 
	plt.savefig(fig_name)

def compare_calls(bedlist1,bedlist2):
	"""
	compare each chunk separately, each comparision yeilds a datapoint in the plot
	"""
	
	xy_tuple = [] # populate these lists with x,y data points 
	portion_calls = 0.0	
	x,y = [0],[0]	
	
	for bin in bedlist1: #0,1,2,..6..num_bins
		exists = 1
		bed1,bed2 = bedlist1[bin],bedlist2[bin]	
	
		bedfile1,bedfile2  = NamedTemporaryFile(suffix=".bed",delete=False),NamedTemporaryFile(suffix=".bed",delete=False)       	
		p = open(bedfile1.name,'a+')
		p.truncate()
		q = open(bedfile2.name,"a+")
		q.truncate()

		for i in bed1:
			writestr = i[0]+"\t"+str(i[1])+"\t"+str(i[2])+"\n" #can be written using a generator
			p.write(writestr)

		for j in bed2:
			writestr = j[0]+"\t"+str(j[1])+"\t"+str(j[2])+"\n"
			q.write(writestr)	
	
		p.close()
		q.close()			
		
		if os.path.getsize(bedfile1.name) == 0 or os.path.getsize(bedfile2.name) == 0:
			print "Truth/test set has no calls!\n"
			exists = 0
			x.append(((size_bin*bin)+size_bin)),y.append(0)	
 
		if exists ==1:
			results = NamedTemporaryFile(suffix=".bed", delete=False)
    			results.close()
			
			#bedtools for doing recirocal overlap between truth and test calls 
			bedtools = "bedtools"  			
			bedtools_check =  os.system("{0} intersect -wa -wb -a {1} -b {2} -f 0.5 -r > {3} "\
					.format(bedtools,bedfile1.name,bedfile2.name,results.name))
			if bedtools_check !=0: 
				print "Bedtools not found!\nExiting.Please ensure you have BEDtools in your bashrc! "
				sys.exit(0)

			wc_command = ("cat {0} | cut -f 1,2,3 | sort | uniq | wc -l".format(results.name)) 
			wc_count = subprocess.check_output(wc_command, shell=True) 
			sensitivity = (float(wc_count))/float(len(open(bedfile1.name).readlines()))	
			x.append(((size_bin*bin))),y.append(sensitivity)	

	xy_tuple.append(x)
	xy_tuple.append(y)
	os.system("rm {0} {1} {2}".format(bedfile1.name,bedfile2.name,results.name)) #cleaning up temp file	
	return xy_tuple
	
def run (list_tru,list_tes):
	"""
	run() controls step-by-step execution of the script. 
	Flow: vcf -> bed format -> intersect truth & test(bedtools) -> sensitivity -> plot
	"""

	bed_chunk_tru,bed_chunk_tes = {},{} #containers for the bed entries

	for invcf in list_tes:
		vcf_name = invcf.strip().split("/")[-1] #making sure you separate out the file name from the path
		bed_chunk_tes[vcf_name] = vcf_to_bed(invcf.strip()) 
		#example: bed_chunk_tes[vcf1] = {bin0:[[1 100 20],[5 30 10], ..],bin1:[[..]}
	
	for invcf in list_tru:
		vcf_name = invcf.strip().split("/")[-1]	
		bed_chunk_tru[vcf_name] = vcf_to_bed(invcf.strip())
	
	figno = 0 #figure numbers for matplotlib	
	for vcfid1 in list_tru:
	
		vid1 = vcfid1.strip().split("/")[-1].strip()
		plot_container = {}
		for vcfid2 in list_tes:	
		 	print "comaparing",vcfid1,vcfid2 	
			vid2 = vcfid2.strip().split("/")[-1].strip()
			plot_data = compare_calls(bed_chunk_tru[vid1],bed_chunk_tes[vid2]) #intersect step to generate data points  
			plot_container[vid2] = plot_data 
		figno = figno + 1	
		plot_sensitivity(plot_container,vid1,figno) #plot data 

def ParseArgs():
	"""
	Argument parser, espects atleast two vcfs to compare 
	"""

	parser = argparse.ArgumentParser()

	parser.add_argument("-tru", type = str, nargs = '+' , required = True,\
			help = "The truth set vcf (or vcfs as a space spearated list)\
				all test vcfs are compared against these ")
        parser.add_argument("-tes", type = str, nargs = '+' , required = True,\
          		help = "The test set vcf (or vcfs as a space spearated list)\
                                Each one of these vcfs is compared against the truth ")
	parser.add_argument("--size-min", dest = "size_min", type = int, default =1, required = False,\
			help = "Floor size of the calls in bp to be considered; default = 1")
	parser.add_argument("--size-max" , dest = "size_max", type = int, default = 3000, required = False,\
			help = "Ceiling size of the calls in bp to be considered ; default = 3000")
	parser.add_argument("--size-bin", dest = "size_bin", type = int, default = 500, required = False,\
			help = "size of the bins for plotting; default = 500")
	parser.add_argument("--pct-ovl", dest = "pct_ovl", type = float, default = 0.5, required = False,\
			help = "minimun percentage reciprocal overlap to keep; default = 0.5")
	return parser.parse_args()

if __name__ == '__main__':

	args = ParseArgs()
	truth_list, test_list = set(args.tru),set(args.tes) #converting to a set to remove redundancy  
	
	global size_min,size_max,size_bin,num_bins,pct_ovl
	size_min, size_max, size_bin, pct_ovl   = args.size_min, args.size_max, args.size_bin, args.pct_ovl
	num_bins = (size_max - size_min + 1 )/size_bin	

	print size_min, size_max, size_bin, pct_ovl, num_bins		
	run(truth_list,test_list)
