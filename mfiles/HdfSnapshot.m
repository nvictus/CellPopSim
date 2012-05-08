classdef HdfSnapshot
    %HDFSNAPSHOT  Extract population snapshot data from PyCps simulation file.
    %   For hdf5 files created using save_snapshot routine. Creating an
    %   instance without specifying a file name will open a dialog window.
    
    properties
        filename
        dataset_names
    end
    
    methods
        function self = HdfSnapshot(filename)
            if nargin == 0
                filename = uigetfile('*.hdf5');
            end
            info = hdf5info(filename);
            names = {info.GroupHierarchy.Datasets.Name}';
            self.dataset_names = cellfun(@(x) x(2:end), names,'uniformoutput',false);            
            self.filename = filename;
        end
        
        function dat = get(self, dset_name)
            dat = hdf5read(self.filename, ['/' dset_name])';
        end
        
        function open_with_hdfview(self)
            if ispc
                [status, result] = system(['"', self.filename, '"']);
            else
                [status, result] = system(['./', self.filename]);
            end
                
            if status
                error('Error opening file. System returned:\n\n%s\n', result);
            end           
        end
        
        function display(self)
            disp('    ');
            disp('HDF5 file containing population snapshot data.')
            disp('    ');
            disp('File name:');
            disp({self.filename});
            disp('Contents:');
            disp(self.dataset_names);
        end
    end
    
end

