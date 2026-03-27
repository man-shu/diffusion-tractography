# The Welsh Advanced Neuroimaging Database (WAND)
**Carolyn Beth McNabb<sup>1</sup>, Ian D Driver<sup>1</sup>, Vanessa Hyde<sup>1</sup>, Garin Hughes<sup>1</sup>, Hannah Louise Chandler<sup>1</sup>, Hannah Thomas<sup>1</sup>, Eirini Messaritaki<sup>1</sup>, Carl Hodgetts<sup>1,2</sup>, Craig Hedge<sup>3</sup>, Christopher Allen<sup>4</sup>, Maria Engel<sup>1</sup>, Sophie Felicity Standen<sup>1</sup>, Emma L Morgan<sup>1</sup>, Elena Stylianopoulou<sup>1</sup>, Svetla Manolova<sup>1</sup>, Lucie Reed<sup>1</sup>, Matthew Ploszajski<sup>1</sup>, Mark Drakesmith<sup>1</sup>, Michael Germuska<sup>1</sup>, Alexander D Shaw<sup>5</sup>, Lars Mueller<sup>6</sup>, Holly Rossiter<sup>1</sup>, Christopher W Davies-Jenkins<sup>7,8</sup>, Tom Lancaster <sup>9</sup>, John Evans<sup>1</sup>, David Owen<sup>1</sup>, Gavin Perry<sup>1</sup>, Slawomir Kusmia<sup>1,10</sup>, Emily Lambe<sup>1</sup>, Adam M Partridge<sup>1</sup>, Allison Cooper<sup>1</sup>, Peter Hobden<sup>1</sup>, Hanzhang Lu<sup>7,8</sup>, Kim S Graham<sup>1,12</sup>, Andrew D Lawrence<sup>1,12</sup>, Richard G Wise<sup>1,13,14</sup>, James T R Walters<sup>15</sup>, Petroc Sumner<sup>1</sup>, Krish D Singh<sup>1</sup>, and Derek K Jones<sup>1</sup>**

<sup>1</sup>Cardiff University Brain Research Imaging Centre, School of Psychology, Cardiff University, Cardiff, United Kingdom, 
<sup>2</sup>Department of Psychology, Royal Holloway, University of London, Egham, United Kingdom, 
<sup>3</sup>School of Psychology, Aston University, Birmingham, United Kingdom, 
<sup>4</sup>Department of Psychology, Durham University, Durham, United Kingdom, 
<sup>5</sup>Washington Singer Laboratories, University of Exeter, Exeter, United Kingdom, 
<sup>6</sup>Leeds Institute of Cardiovascular and Metabolic Medicine, University of Leeds, Leeds, United Kingdom, 
<sup>7</sup>The Russel H. Morgan Department of Radiology and Radiological Science, Johns Hopkins University School of Medicine, Baltimore, Maryland, USA,
<sup>8</sup>F.M. Kirby Research Center for Functional Brain Imaging, Kennedy Kreiger Institute, Baltimore, Maryland, USA,
<sup>9</sup>Department of Psychology, University of Bath, Bath, United Kingdom, 
<sup>10</sup>IBM Polska Sp. z o. o., Department of Content Design, Cracow, Poland
<sup>11</sup>University of Sheffield, Research Services, New Spring House, 231 Glossop Road, Sheffield, S10 2GW, UK
<sup>12</sup>School of Philosophy, Psychology and Language Sciences, Dugald Stewart Building, University of Edinburgh, 3 Charles Street, Edinburgh, EH8 9AD, UK
<sup>13</sup>Department of Neurosciences, Imaging, and Clinical Sciences, 'G. D'Annunzio' University of Chieti-Pescara, Chieti, Italy,
<sup>14</sup>Institute for Advanced Biomedical Technologies, 'G. D'Annunzio' University of Chieti-Pescara, Chieti, Italy
<sup>15</sup>School of Medicine, Centre for Neuropsychiatric Genetics and Genomics, Cardiff University, Cardiff, United Kingdom


### Acknowledgements:
The WAND data were acquired at the UK National Facility for In Vivo MR Imaging of Human Tissue Microstructure funded by the EPSRC (grant EP/M029778/1), and The Wolfson Foundation, and supported by a Wellcome Trust Investigator Award (096646/Z/11/Z) and a Wellcome Trust Strategic Award (104943/Z/14/Z). The UK Medical Research Council (MR/M008932/1), the Welsh Government and Cardiff University provide funding support for the CUBRIC ultra-high field imaging facility.

The authors would like to thank:
Thomos Wizel (formally MGH, now GBIO) for his help setting up the diffusion sequences on the Connectom scanner. 
Olivier Mougin (University of Nottingham) for developing the phase-sensitive inversion recovery and T1 code. 
William Clarke (Oxford University) for providing the image reconstruction code for the MP2RAGE.

Many researchers in the Cardiff University Brain Research Imaging Centre (CUBRIC) contributed their time and expertise throughout the project. The authors would like to especially thank Mara Cercignani and Marco Palombo for their help with quantitative and diffusion imaging questions, the CUBRIC IT team for their help with storage, and data organisation, and the CUBRIC reception team for their help with participant admin.


### Dataset description:
The Welsh Advanced Neuroimaging Database (WAND) is a multi-scale, multi-modal imaging database of the healthy human brain. It includes non-invasive *in vivo* brain data from 3T MRI with ultra-strong (300mT/m) magnetic field gradients (especially designed for evaluating tissue microstructure), 7T and 3T MRI and nuclear magnetic resonance spectroscopy (MRS), and MEG. The dataset also includes cognitive and behavioural data that allow for investigation of brain-behaviour interactions at multiple spatial and temporal scales.

### Data naming structure and organisation:

Data have been organised using the [Brain Imaging Data Structure (BIDS)](https://www.nature.com/articles/sdata201644). Where BIDS specifications were not available, we have consulted with experts in the field to align as closely as possible with this data structure.

BIDS naming conventions for many of the Connectom (ses-02) acquisitions are still in their infancy - we have used names as close as we can to the existing rules and bent these slightly where recommended by experts.<br>

>**qMT**<br>
FlipAngle and MTOffsetFrequency for quantitative MRI are labelled according to specifications outlined in the qMRLab BIDS recommendations. See [here](https://qmrlab.readthedocs.io/en/master/qmt_spgr_batch.html). For qMT data, we have used the `mt-` entity to index the `MTOffsetFrequency` - this is against the official BIDS specification (on/off only) but allowed for better definition between qMT scans.<br>
N.B. `mt-1` will refer to the first MTOffsetFrequency for *that* flip angle (e.g. `flip-1`), meaning that `flip-1_mt-1` could refer to a different MTOffsetFrequency than `flip-2_mt-1`. For details on flip angle and MT offset frequency, refer to the .json file for that image.<br>  

>**mcDESPOT** <br>
mcDESPOT images are labelled according to specifications outlined in the Quantitative MRI BIDS documentation [here](https://bids-specification.readthedocs.io/en/stable/99-appendices/11-qmri.html#deriving-the-intended-qmri-application-from-an-ambiguous-file-collection). For mcDESPOT data, we have used the `acq-` entity to index between `spgr`, `spgr_IR` and `SSFP` acquisitions. We have used the Variable Flip Angle `VFA` modality label to define mcDESPOT scans.<br>
Thanks to Agah Karakuzu for recommendations on BIDS formatting for quantitiative MRI.<br>

>**AxCaliber**<br>
For AxCaliber and CHARMED, we have used the `acq-` entity to index the scan sequence: `AxCaliber` or `CHARMED`. Both have `dwi` as their modality label.<br>
Big delta values for the AxCaliber scans are added to the .json file as `t_bdel` in keeping with recommendations from the aDWI-BIDS [preprint](https://arxiv.org/pdf/2103.14485.pdf). The `acq-` label is used to define which AxCaliber scan the image came from. `acq-AxCaliber1` refers to the "AX_delta17p3_30xb2200_30xb4400" scan, `acq-AxCaliber2` to the "AX_delta30_30xb4000_30xb8000" scan and so on. The P>A reference scan is referred to as `acq-AxCaliberRef`.

**Some data will fail the BIDS validation**<br>
This is relevant for the MEG, MRS and TMS data, where data are stored as .mat or .dat files. However, the folder structure and naming convention will still be in keeping with the rest of the dataset.

### Data availability:
Raw data have been made available, along with brain extracted T1 images, and quality metrics for multishell diffusion, T1, T2 and functional (BOLD) data. These are available in the `derivatives` folder of our [GitLab repository](https://git.cardiff.ac.uk/cubric/wand)..

**Here we provide instructions for downloading and interacting with the WAND data using [GIN](https://gin.g-node.org/G-Node/info/wiki). GIN will allow you to interrogate and work with the data without requiring terabytes of storage space.**

If you are having trouble accessing the dataset, please send an email to cubricwand@cardiff.ac.uk


## External user instructions
The WAND data are hosted on the [G-Node GIN repository](https://gin.g-node.org/CUBRIC/WAND). To access the data, please follow [these instructions](https://gin.g-node.org/G-Node/info/wiki).

#### Checklist (have you done all these steps?)
- Sign up to the G-Node GIN service using the **Register** button at the top of the [Homepage](https://gin.g-node.org) (or click [here](https://gin.g-node.org/user/sign_up))
- Make sure you have `conda` installed. See [here](https://docs.conda.io/projects/miniconda/en/latest/) for installation instructions.
- Install `git-annex` (using `conda`) using [these instructions](https://git-annex.branchable.com/install)
- Install the `gin` command-line client following [these instructions](https://gin.g-node.org/G-Node/Info/wiki/GIN+CLI+Setup)
- Add your public SSH key [here](https://gin.g-node.org/user/settings/ssh) and sign in with the client using `gin login`.

You will now be able to clone the repository to your machine. First, change into the directory where you want the repository to download. In the terminal window, type:
```
cd </path/to/newhome>
```
And then use gin to pull down the repository:
```
gin get CUBRIC/WAND
cd WAND
cat README.md
```
By default, large files will not be downloaded automatically. You will be able to *see* them but not open them. To download larger files, use the command:
```
gin get-content <large-file>
```
And to remove downloaded files:
```
gin remove-content .        # remove all downloaded files
gin remove-content folder/  # remove a particular folder
```

You should now have access to the full WAND dataset. 

**PLEASE BE AWARE THAT THE DATASET IS HUGE - WE DO NOT ADVISE USING `gin get-content *` UNLESS YOU HAVE A LOT OF SPACE AND A LOT OF TIME TO WAIT FOR THE DATA TO FINISH DOWNLOADING.** Instead, we recommend only downloading the data you need, as you need it.


## Additional scripts
In addition to the data release itself, we have shared some code, used to run quality control on the diffusion data using FSL's eddy_qc and the T1, T2 and BOLD functional data using MRIqc. These can be found in the `code` folder of our [GitLab repository](https://git.cardiff.ac.uk/cubric/wand).

## MEG-MRI Coregistrations
For those interested in MEG, we supply the coregistered MRI data in our [GitLab repository](https://git.cardiff.ac.uk/cubric/wand/-/tree/main/ancillary_files/meg/Coregistered_MRI_scans?ref_type=heads). 

## Physiological data
Physiological monitoring data for some functional scans are currently unavailable. The research team is working hard to ensure these data are made available as soon as possible.

