## Location of all the files saved and read by the ConsistencyCheck

if [ ! -d $ConsistencyCacheDirectory ]
then
    mkdir -p $ConsistencyCacheDirectory
fi

## Age (in sec) of uberftp output before walking again
export SiteDirListAge=30240

## Age (in sec) of DatasetsInPhedex.dat file before it is redownloaded
export DatasetsInPhedexAge=86400

## Maximum number of simultaneous wgets calls to Phedex
export NumPhedexThreads=2

## Age (in sec) of list of files in Phedex before redownloading
export PhedexOutputAge=30240

## Location of webpages
export ConsistencyWebpages=~/public_html/ConsistencyCheck

## List of SEs

locateOutput=$ConsistencyCacheDirectory/se_list.txt
xrdfs xrootd-redic.pi.infn.it locate -h /store/ > $locateOutput
xrdfs cmsxrootd1.fnal.gov locate -h /store/ >> $locateOutput

export SE_T2_AT_Vienna=`cat $locateOutput | grep .cscs.ch: | awk 'BEGIN { FS = ":" } { print $1 }'`
export SE_T2_BE_IIHE=maite.iihe.ac.be
export SE_T2_BE_UCL=ingrid-se02.cism.ucl.ac.be
export SE_T2_BR_SPRACE=osg-se.sprace.org.br
export SE_T2_CH_CSCS=`cat $locateOutput | grep .cscs.ch: | awk 'BEGIN { FS = ":" } { print $1 }'`
export SE_T2_ES_CIEMAT=srm.ciemat.es
export SE_T2_US_Caltech=cit-se.ultralight.org
export SE_T2_US_Florida=srm.ihepa.ufl.edu
export SE_T2_US_MIT=`cat $locateOutput | grep .mit.edu: | awk 'BEGIN { FS = ":" } { print $1 }'`
export SE_T2_US_Nebraska=`cat $locateOutput | grep .unl.edu: | awk 'BEGIN { FS = ":" } { print $1 }'`
export SE_T2_US_UCSD=`cat $locateOutput | grep .ucsd.edu: | awk 'BEGIN { FS = ":" } { print $1 }'`
export SE_T3_CH_PSI=t3se01.psi.ch
